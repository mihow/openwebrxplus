"""
Signal Classifier Module for OpenWebRX+

Uses TorchSig for automatic signal classification and modulation recognition.
Analyzes IQ samples and predicts the modulation type.
"""

from owrx.config import Config
from owrx.feature import FeatureDetector
from csdr.module import ThreadModule
from pycsdr.types import Format
import threading
import numpy as np
import json
import time

import logging

logger = logging.getLogger(__name__)


# TorchSig Sig53 class names mapped to OpenWebRX+ mode names
TORCHSIG_TO_OWRX_MODE = {
    # Analog modulations
    "ook": "cw",
    "am-dsb": "am",
    "am-dsb-sc": "am",
    "am-lsb": "lsb",
    "am-usb": "usb",
    "fm": "nfm",
    "wbfm": "wfm",
    "lfm": None,
    # PSK modulations
    "bpsk": "bpsk31",
    "qpsk": None,
    "8psk": None,
    "16psk": None,
    "32psk": None,
    "64psk": None,
    # QAM modulations
    "16qam": None,
    "32qam": None,
    "64qam": None,
    "128qam": None,
    "256qam": None,
    "512qam": None,
    "1024qam": None,
    # FSK modulations
    "2fsk": "rtty170",
    "4fsk": "dmr",
    "8fsk": None,
    "16fsk": None,
    "2gfsk": None,
    "4gfsk": "dmr",
    "8gfsk": None,
    "16gfsk": None,
    "2msk": None,
    "4msk": None,
    "8msk": None,
    "16msk": None,
    "gmsk": "dstar",
    # OFDM modulations
    "ofdm-64": "ft8",
    "ofdm-72": None,
    "ofdm-128": None,
    "ofdm-180": None,
    "ofdm-256": None,
    "ofdm-300": None,
    "ofdm-512": None,
    "ofdm-600": None,
    "ofdm-900": None,
    "ofdm-1024": None,
    "ofdm-1200": None,
    "ofdm-2048": "dab",
}

# Sig53 class index to class name mapping
SIG53_CLASSES = [
    "ook", "4ask", "8ask", "bpsk", "qpsk", "8psk", "16psk", "32psk", "64psk",
    "16qam", "32qam", "64qam", "128qam", "256qam", "512qam", "1024qam",
    "2fsk", "4fsk", "8fsk", "16fsk", "2gfsk", "4gfsk", "8gfsk", "16gfsk",
    "2msk", "4msk", "8msk", "16msk", "gmsk",
    "ofdm-64", "ofdm-72", "ofdm-128", "ofdm-180", "ofdm-256", "ofdm-300",
    "ofdm-512", "ofdm-600", "ofdm-900", "ofdm-1024", "ofdm-1200", "ofdm-2048",
    "am-dsb", "am-dsb-sc", "am-lsb", "am-usb", "fm", "lfm", "lfm_ramp",
    "lfm_triangle", "continuous_phase_fsk", "dvb-s2", "chirp_ss"
]


class SignalClassifierModel:
    """
    Wrapper for TorchSig model loading and inference.
    Handles lazy loading and caching of the model.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def getInstance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = SignalClassifierModel()
        return cls._instance

    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.loaded = False
        self.load_error = None

    def load(self, device: str = "cpu"):
        """Load the TorchSig model if not already loaded."""
        if self.loaded:
            return True

        try:
            import torch
            from torchsig.models import efficientnet_b0

            self.device = device
            logger.info("Loading TorchSig model on device: %s", device)

            # Load pre-trained EfficientNet-B0 for Sig53 classification
            self.model = efficientnet_b0(
                pretrained=True,
                num_classes=len(SIG53_CLASSES)
            )
            self.model.to(self.device)
            self.model.eval()
            self.loaded = True
            logger.info("TorchSig model loaded successfully")
            return True

        except Exception as e:
            self.load_error = str(e)
            logger.error("Failed to load TorchSig model: %s", e)
            return False

    def classify(self, iq_samples: np.ndarray, top_k: int = 3) -> list:
        """
        Classify IQ samples and return top-k predictions.

        Args:
            iq_samples: Complex64 numpy array of IQ samples
            top_k: Number of top predictions to return

        Returns:
            List of dicts with 'class', 'confidence', 'owrx_mode' keys
        """
        if not self.loaded:
            return []

        try:
            import torch

            # Prepare input - convert complex IQ to tensor
            samples = np.array(iq_samples, dtype=np.complex64)

            # Normalize samples
            max_val = np.abs(samples).max()
            if max_val > 0:
                samples = samples / max_val

            # Convert to tensor format expected by model
            # TorchSig models expect (batch, 2, time) for IQ
            iq_tensor = torch.zeros(1, 2, len(samples))
            iq_tensor[0, 0, :] = torch.from_numpy(samples.real.astype(np.float32))
            iq_tensor[0, 1, :] = torch.from_numpy(samples.imag.astype(np.float32))
            iq_tensor = iq_tensor.to(self.device)

            # Run inference
            with torch.no_grad():
                output = self.model(iq_tensor)
                probs = torch.softmax(output, dim=1)

            # Get top-k predictions
            values, indices = torch.topk(probs[0], min(top_k, len(SIG53_CLASSES)))

            predictions = []
            for prob, idx in zip(values.cpu().numpy(), indices.cpu().numpy()):
                class_name = SIG53_CLASSES[idx] if idx < len(SIG53_CLASSES) else "unknown"
                owrx_mode = TORCHSIG_TO_OWRX_MODE.get(class_name)
                predictions.append({
                    "torchsig_class": class_name,
                    "confidence": float(prob),
                    "mode": owrx_mode
                })

            return predictions

        except Exception as e:
            logger.error("Classification error: %s", e)
            return []


class SignalClassifier(ThreadModule):
    """
    Thread-based signal classifier module that processes IQ samples
    and outputs JSON predictions.
    """
    def __init__(self, sampleRate: int = 48000, interval: float = 1.0,
                 threshold: float = 0.3, device: str = "cpu"):
        self.sampleRate = sampleRate
        self.interval = interval
        self.threshold = threshold
        self.device = device
        self.frequency = 0
        self.buffer = []
        self.buffer_size = int(sampleRate * interval)
        self.last_classification = 0

        # Get the shared model instance
        self.model = SignalClassifierModel.getInstance()

        super().__init__()

    def getInputFormat(self) -> Format:
        return Format.COMPLEX_FLOAT

    def getOutputFormat(self) -> Format:
        return Format.CHAR

    def setDialFrequency(self, frequency: int) -> None:
        self.frequency = frequency

    def run(self):
        logger.info("SignalClassifier starting (rate=%d, interval=%.1fs)",
                    self.sampleRate, self.interval)

        # Load model on first run
        if not self.model.loaded:
            self.model.load(self.device)

        while self.doRun:
            # Read IQ samples
            try:
                data = self.reader.read()
            except ValueError:
                break

            if data is None:
                break

            # Convert bytes to complex float
            try:
                samples = np.frombuffer(data, dtype=np.complex64)
                self.buffer.extend(samples)
            except Exception as e:
                logger.error("Error reading samples: %s", e)
                continue

            # Check if it's time to classify
            now = time.time()
            if len(self.buffer) >= self.buffer_size and (now - self.last_classification) >= self.interval:
                self.last_classification = now

                # Get samples for classification
                classify_samples = np.array(self.buffer[:self.buffer_size])
                self.buffer = self.buffer[self.buffer_size:]

                # Run classification
                predictions = self.model.classify(classify_samples, top_k=3)

                # Filter by threshold and create output
                filtered = [p for p in predictions if p["confidence"] >= self.threshold]

                if filtered and self.writer is not None:
                    output = {
                        "timestamp": int(now * 1000),
                        "freq": self.frequency,
                        "predictions": filtered,
                        "sample_rate": self.sampleRate
                    }

                    # Output as JSON line
                    json_line = json.dumps(output) + "\n"
                    try:
                        self.writer.write(json_line.encode("utf-8"))
                    except Exception as e:
                        logger.error("Error writing output: %s", e)

        logger.info("SignalClassifier exiting")


def is_available() -> bool:
    """Check if signal classifier feature is available."""
    return FeatureDetector().is_available("signal_classifier")


def get_config():
    """Get signal classifier configuration from settings."""
    pm = Config.get()
    return {
        "enabled": pm.get("signal_classifier_enabled", False),
        "threshold": pm.get("signal_classifier_threshold", 0.5),
        "interval": pm.get("signal_classifier_interval", 1.0),
        "device": pm.get("signal_classifier_device", "cpu"),
    }
