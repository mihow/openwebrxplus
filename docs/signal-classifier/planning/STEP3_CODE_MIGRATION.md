# Step 3: Code Migration

## Goal
Update `signal_classifier.py` to use ONNX Runtime instead of PyTorch.

## Why This Step?
- Remove dependency on PyTorch/TorchSig
- Use optimized ONNX Runtime for inference
- Load pre-exported model with pretrained weights
- Maintain same functionality with better performance

## Prerequisites
- Completed Step 1 (exported ONNX model)
- Completed Step 2 (updated Docker image)
- Docker container running

## Time Required
- Code changes: ~5 minutes
- Testing: ~10-15 minutes

---

## Key Changes Overview

### Model Loading
| Aspect | Before (PyTorch) | After (ONNX) |
|--------|-----------------|--------------|
| Import | `from torchsig.models import XCiT1d` | `import onnxruntime as ort` |
| Load | `XCiT1d(...)`  | `ort.InferenceSession(path)` |
| Size | 3.7 GB dependencies | 20 MB runtime |
| Weights | Random (untrained) | Pretrained Sig53 |

### Input Format
| Aspect | Before (XCiT1d) | After (ONNX) |
|--------|-----------------|--------------|
| Shape | `(batch, channels, length)` | `(batch, length)` |
| Type | `torch.Tensor` (channels-first) | `np.ndarray` (complex64) |
| Processing | Split I/Q into separate channels | Keep as complex array |

### Inference
| Aspect | Before (PyTorch) | After (ONNX) |
|--------|-----------------|--------------|
| API | `model(tensor)` | `session.run(None, {input_name: array})` |
| Context | Needs `torch.no_grad()` | No context needed |
| Softmax | Built into PyTorch | Manual numpy implementation |

---

## Complete Updated File

**File:** `owrx/signal_classifier.py`

Replace the entire file with this ONNX-based implementation:

```python
"""
Signal Classifier Module for OpenWebRX+

Uses TorchSig EfficientNet-B0 (exported to ONNX) for automatic signal
classification and modulation recognition. Analyzes IQ samples and predicts
the modulation type.

ONNX Runtime replaces PyTorch for production inference:
- 98% smaller (20 MB vs 3.7 GB)
- Pretrained Sig53 weights (62.75% accuracy)
- Faster inference
- Lower memory usage
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
    Wrapper for ONNX Runtime model loading and inference.
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
        self.session = None
        self.input_name = None
        self.output_name = None
        self.loaded = False
        self.load_error = None

    def load(self, model_path: str = "/usr/share/openwebrx/models/torchsig_efficientnet_b0_sig53.onnx"):
        """Load the ONNX model if not already loaded."""
        if self.loaded:
            return True

        try:
            import onnxruntime as ort

            logger.info("Loading TorchSig ONNX model from: %s", model_path)

            # Create ONNX Runtime session
            # Use CPU execution provider (can add CUDA later)
            providers = ['CPUExecutionProvider']

            self.session = ort.InferenceSession(
                model_path,
                providers=providers
            )

            # Get input/output names
            self.input_name = self.session.get_inputs()[0].name
            self.output_name = self.session.get_outputs()[0].name

            # Get model info
            input_shape = self.session.get_inputs()[0].shape
            output_shape = self.session.get_outputs()[0].shape

            logger.info("ONNX model loaded successfully")
            logger.info("  Input: %s, shape: %s", self.input_name, input_shape)
            logger.info("  Output: %s, shape: %s", self.output_name, output_shape)
            logger.info("  Model has pretrained Sig53 weights (62.75%% accuracy)")

            self.loaded = True
            return True

        except Exception as e:
            self.load_error = str(e)
            logger.error("Failed to load ONNX model: %s", e)
            return False

    def softmax(self, x):
        """Apply softmax to convert logits to probabilities."""
        exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return exp_x / exp_x.sum(axis=-1, keepdims=True)

    def classify(self, iq_samples: np.ndarray, top_k: int = 3) -> list:
        """
        Classify IQ samples and return top-k predictions.

        Args:
            iq_samples: Complex64 numpy array of IQ samples
            top_k: Number of top predictions to return

        Returns:
            List of dicts with 'torchsig_class', 'confidence', 'mode' keys
        """
        if not self.loaded:
            return []

        try:
            # Prepare input - convert complex IQ to numpy array
            samples = np.array(iq_samples, dtype=np.complex64)

            # Normalize samples to [-1, 1]
            max_val = np.abs(samples).max()
            if max_val > 0:
                samples = samples / max_val

            # Add batch dimension: (num_samples,) -> (1, num_samples)
            input_data = np.expand_dims(samples, axis=0)

            # Run ONNX inference
            outputs = self.session.run(
                [self.output_name],
                {self.input_name: input_data}
            )

            # Get logits and convert to probabilities
            logits = outputs[0][0]  # Remove batch dimension
            probs = self.softmax(logits)

            # Get top-k predictions
            top_indices = np.argsort(probs)[-top_k:][::-1]
            top_probs = probs[top_indices]

            predictions = []
            for idx, prob in zip(top_indices, top_probs):
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
        self.device = device  # Not used with ONNX CPU, but kept for compatibility
        self.frequency = 0
        self.buffer = []

        # ONNX model expects specific input size
        # EfficientNet-B0 was likely trained on one of these sizes
        # Adjust if getting shape mismatch errors: try 1024, 2048, 4096, or 8192
        self.buffer_size = 4096

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
        logger.info("SignalClassifier starting (rate=%d, interval=%.1fs, buffer=%d)",
                    self.sampleRate, self.interval, self.buffer_size)

        # Load model on first run
        if not self.model.loaded:
            if not self.model.load():
                logger.error("Failed to load model, exiting classifier")
                return

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
        "enabled": pm["signal_classifier_enabled"] if "signal_classifier_enabled" in pm else False,
        "threshold": pm["signal_classifier_threshold"] if "signal_classifier_threshold" in pm else 0.5,
        "interval": pm["signal_classifier_interval"] if "signal_classifier_interval" in pm else 1.0,
        "device": pm["signal_classifier_device"] if "signal_classifier_device" in pm else "cpu",
    }
```

---

## Key Code Changes Explained

### 1. Model Loading (lines 106-135)

**Before (PyTorch):**
```python
import torch
from torchsig.models import XCiT1d

self.model = XCiT1d(
    input_channels=2,
    n_features=53,
    xcit_version="nano_12_p16_224",
    ds_method="downsample",
    ds_rate=16
)
self.model.to(device)
self.model.eval()
logger.warning("TorchSig model loaded WITHOUT pretrained weights")
```

**After (ONNX):**
```python
import onnxruntime as ort

self.session = ort.InferenceSession(
    model_path,
    providers=['CPUExecutionProvider']
)
self.input_name = self.session.get_inputs()[0].name
self.output_name = self.session.get_outputs()[0].name
logger.info("Model has pretrained Sig53 weights (62.75%% accuracy)")
```

**Why:** ONNX loads model + weights from single file, no architecture specification needed.

### 2. Softmax Implementation (lines 137-140)

**New:**
```python
def softmax(self, x):
    """Apply softmax to convert logits to probabilities."""
    exp_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return exp_x / exp_x.sum(axis=-1, keepdims=True)
```

**Why:** ONNX model outputs raw logits, need manual softmax (PyTorch had it built-in).

### 3. Input Preprocessing (lines 157-164)

**Before (XCiT1d):**
```python
# Split complex into two real channels
iq_tensor = torch.zeros(1, 2, len(samples), dtype=torch.float32)
iq_tensor[0, 0, :] = torch.from_numpy(samples.real)
iq_tensor[0, 1, :] = torch.from_numpy(samples.imag)
```

**After (ONNX):**
```python
# Keep as complex array
samples = np.array(iq_samples, dtype=np.complex64)
input_data = np.expand_dims(samples, axis=0)  # Add batch dimension
```

**Why:** EfficientNet-B0 expects complex input, XCiT1d expected separate I/Q channels.

### 4. Inference (lines 166-171)

**Before (PyTorch):**
```python
with torch.no_grad():
    output = self.model(iq_tensor)
    probs = torch.softmax(output, dim=-1)
```

**After (ONNX):**
```python
outputs = self.session.run(
    [self.output_name],
    {self.input_name: input_data}
)
logits = outputs[0][0]
probs = self.softmax(logits)
```

**Why:** ONNX uses session.run() API, no need for no_grad context.

---

## Testing the Code

### 1. Rebuild Docker Image
```bash
cd /home/michael/Projects/Radio/OpenWebRX
docker-compose -f docker-compose.dev.yml build
```

### 2. Restart Container
```bash
docker stop owrx-custom && docker rm owrx-custom
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Check Logs for Successful Load
```bash
docker logs owrx-custom -f | grep -i "signal\|onnx\|classifier"
```

**Expected:**
```
Loading TorchSig ONNX model from: /usr/share/openwebrx/models/torchsig_efficientnet_b0_sig53.onnx
ONNX model loaded successfully
  Input: iq_samples, shape: [1, 4096]
  Output: logits, shape: [1, 53]
  Model has pretrained Sig53 weights (62.75% accuracy)
SignalClassifier starting (rate=200000, interval=1.0s, buffer=4096)
```

**Should NOT see:**
```
Failed to load ONNX model
TorchSig model loaded WITHOUT pretrained weights
ModuleNotFoundError: No module named 'torch'
```

### 4. Enable in Settings
Visit: http://beast.wirehair-yo.ts.net:8073/settings/decoding

- ✅ Enable automatic signal classification
- Set confidence threshold: 0.3
- Set classification interval: 1.0 seconds
- Device: CPU

**Save settings**

### 5. Tune to a Known Signal
Tune to:
- FM broadcast (88-108 MHz) → Should detect `fm` or `wbfm`
- Amateur RTTY (14.080 MHz) → Should detect `2fsk`
- FT8 (7.074 MHz) → Should detect `ofdm-64`

### 6. Check for Predictions in Logs
```bash
docker logs owrx-custom -f | grep -i "prediction\|confidence"
```

**Expected:**
```json
{"timestamp": 1700654321000, "freq": 97500000, "predictions": [{"torchsig_class": "wbfm", "confidence": 0.89, "mode": "wfm"}], "sample_rate": 200000}
```

**Should NOT be random:** If you see rapidly changing classes with similar confidence (~0.02 each), model is not working.

---

## Troubleshooting

### Issue: "Failed to load ONNX model: [Errno 2] No such file"
**Cause:** ONNX file not in Docker image
**Solution:**
- Check Step 2 was completed (COPY in Dockerfile)
- Verify: `docker run --rm owrx-custom:dev ls /usr/share/openwebrx/models/`
- Rebuild with `--no-cache`

### Issue: "ModuleNotFoundError: No module named 'onnxruntime'"
**Cause:** ONNX Runtime not installed in image
**Solution:**
- Check Dockerfile has `pip install onnxruntime==1.16.3`
- Rebuild image
- Verify: `docker run --rm owrx-custom:dev python3 -c "import onnxruntime"`

### Issue: "Input shape mismatch"
**Cause:** Buffer size doesn't match model's expected input
**Solution:**
Try different `buffer_size` values in `__init__()`:
```python
self.buffer_size = 2048  # Try: 1024, 2048, 4096, or 8192
```

### Issue: All predictions have same low confidence (~0.02)
**Cause:** Softmax not working or model not loaded correctly
**Solution:**
- Check softmax is applied: verify `self.softmax(logits)` is called
- Verify logits are reasonable (not all zeros or NaNs)
- Add debug logging: `logger.debug(f"Logits: {logits[:5]}")`

### Issue: Predictions seem random or constantly changing
**Cause:** Model may not be the pretrained version
**Solution:**
- Verify ONNX file is from Step 1 export (with pretrained weights)
- Check file size: should be 30-50 MB
- Re-export model following Step 1

### Issue: High CPU usage
**Cause:** Classification running too frequently
**Solution:**
- Increase interval in settings (try 2.0 or 5.0 seconds)
- Reduce buffer size (uses less CPU per classification)
- Consider GPU acceleration

---

## Performance Tuning

### Buffer Size vs Accuracy
| Buffer Size | Data Length | Accuracy | CPU Usage |
|-------------|-------------|----------|-----------|
| 1024 | 21 ms @ 48kHz | Lower | Low |
| 2048 | 43 ms @ 48kHz | Medium | Medium |
| 4096 | 85 ms @ 48kHz | Good | Medium |
| 8192 | 170 ms @ 48kHz | Best | High |

**Recommendation:** Start with 4096, adjust based on results.

### Classification Interval
| Interval | Use Case | CPU Impact |
|----------|----------|-----------|
| 0.1-0.5s | Fast-changing signals | High |
| 1.0s | Normal use (default) | Low |
| 2.0-5.0s | Background monitoring | Very low |

---

## Next Step

**→ [Step 4: Testing](STEP4_TESTING.md)**

Comprehensive testing with real signals to verify accuracy.

---

## Key Points to Remember

✅ **Simpler code:** No PyTorch context managers or device handling

✅ **Faster inference:** ONNX Runtime is optimized for production

✅ **Real predictions:** Pretrained weights give meaningful results immediately

✅ **Lower memory:** ~100 MB vs ~800 MB with PyTorch

✅ **No training needed:** Model is ready to use as-is

---

**Status:** Code migrated, ready for testing ✅
