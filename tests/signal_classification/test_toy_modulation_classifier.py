"""
Toy modulation classifier test.

This test demonstrates the end-to-end flow of signal classification:
signal -> features -> pretrained model -> predicted modulation

The test generates synthetic IQ signals for several modulation types (AM, FM, CW, SSB),
extracts simple features, loads a tiny PyTorch classifier with deterministic weights,
and asserts that predictions match the expected modulation type.

Requirements:
    - numpy
    - torch

To run:
    pytest tests/signal_classification/test_toy_modulation_classifier.py -v
"""

import numpy as np
import torch
import torch.nn as nn
from unittest import TestCase

# Import pretrained weights from the signal_classification module
# Use absolute import that works when running tests from repo root
from openwebrxplus.signal_classification.toy_pretrained_weights import LABELS, W, b


class SyntheticSignalGenerator:
    """Generates synthetic IQ signals for various modulation types."""

    def __init__(self, sample_rate: int = 48000, duration: float = 0.1, seed: int = 42):
        """
        Initialize the signal generator.

        Args:
            sample_rate: Sample rate in Hz
            duration: Signal duration in seconds
            seed: Random seed for reproducibility
        """
        self.sample_rate = sample_rate
        self.duration = duration
        self.num_samples = int(sample_rate * duration)
        self.rng = np.random.default_rng(seed)
        self.t = np.arange(self.num_samples) / sample_rate

    def generate_am(
        self, carrier_freq: float = 1000.0, mod_freq: float = 100.0, mod_depth: float = 0.8
    ) -> np.ndarray:
        """
        Generate AM signal.

        AM has varying envelope (amplitude modulation) but constant instantaneous frequency.
        """
        carrier = np.exp(1j * 2 * np.pi * carrier_freq * self.t)
        modulation = 1 + mod_depth * np.sin(2 * np.pi * mod_freq * self.t)
        return carrier * modulation

    def generate_fm(
        self, carrier_freq: float = 1000.0, mod_freq: float = 100.0, freq_deviation: float = 2000.0
    ) -> np.ndarray:
        """
        Generate FM signal.

        FM has constant envelope but varying instantaneous frequency.
        Higher freq_deviation creates more inst_freq variance.
        """
        phase = (
            2 * np.pi * carrier_freq * self.t
            + (freq_deviation / mod_freq) * np.sin(2 * np.pi * mod_freq * self.t)
        )
        return np.exp(1j * phase)

    def generate_cw(self, carrier_freq: float = 1000.0) -> np.ndarray:
        """
        Generate CW (Continuous Wave) signal.

        CW is a pure sinusoid with constant envelope and frequency.
        """
        return np.exp(1j * 2 * np.pi * carrier_freq * self.t)

    def generate_ssb(
        self, base_freq: float = 1000.0, bandwidth: float = 3000.0
    ) -> np.ndarray:
        """
        Generate SSB-like signal (simulated as filtered noise).

        SSB has moderate envelope and frequency variations, similar to voice.
        """
        # Generate band-limited noise to simulate SSB
        noise = self.rng.standard_normal(self.num_samples) + 1j * self.rng.standard_normal(
            self.num_samples
        )

        # Apply bandpass filter (simple windowed approach)
        freqs = np.fft.fftfreq(self.num_samples, 1 / self.sample_rate)
        spectrum = np.fft.fft(noise)

        # Bandpass around base_freq to base_freq + bandwidth
        mask = (freqs >= base_freq) & (freqs <= base_freq + bandwidth)
        spectrum[~mask] = 0

        signal = np.fft.ifft(spectrum)
        # Normalize
        signal = signal / np.max(np.abs(signal)) * 0.5
        return signal


class FeatureExtractor:
    """Extracts simple features from IQ signals for classification."""

    def compute_envelope(self, iq_signal: np.ndarray) -> np.ndarray:
        """Compute signal envelope (magnitude)."""
        return np.abs(iq_signal)

    def compute_instantaneous_frequency(self, iq_signal: np.ndarray) -> np.ndarray:
        """Compute instantaneous frequency from phase derivative."""
        phase = np.unwrap(np.angle(iq_signal))
        inst_freq = np.diff(phase) / (2 * np.pi)
        return inst_freq

    def compute_spectral_peak_ratio(self, iq_signal: np.ndarray) -> float:
        """Compute ratio of peak to mean in the spectrum."""
        spectrum = np.abs(np.fft.fft(iq_signal))
        peak = np.max(spectrum)
        mean = np.mean(spectrum)
        # Avoid division by zero
        return float(peak / mean) if mean > 0 else 0.0

    def extract_features(self, iq_signal: np.ndarray) -> np.ndarray:
        """
        Extract normalized features from an IQ signal.

        Features are designed to separate modulation types:
        - envelope_var: High for AM, near-zero for FM/CW, low for SSB
        - inst_freq_var: Near-zero for AM/CW, moderate for FM, high for SSB
        - log_peak_ratio: Very high for CW, moderate for AM/FM, low for SSB

        Returns:
            Array of shape (3,) containing:
                - envelope variance (scaled)
                - instantaneous frequency variance (scaled)
                - log of spectral peak ratio (normalized)
        """
        envelope = self.compute_envelope(iq_signal)
        inst_freq = self.compute_instantaneous_frequency(iq_signal)

        # Compute variances
        env_var = np.var(envelope)
        inst_freq_var = np.var(inst_freq)
        spectral_peak_ratio = self.compute_spectral_peak_ratio(iq_signal)

        # Scale features to match the weight matrix expectations
        # env_var: scale by 2.5 so typical AM (0.4) -> 1.0
        env_var_scaled = env_var * 2.5

        # inst_freq_var: scale by 1000 so typical SSB (0.001) -> 1.0
        inst_freq_var_scaled = inst_freq_var * 1000

        # Use log of peak ratio and normalize
        # log(peak_ratio) typically 3.7 (SSB) to 8.5 (CW)
        # Normalize: (log_peak - 6.0) / 2.5 gives range roughly -0.9 to 1.0
        # Add 1 to spectral_peak_ratio to avoid log(0) when signal has zero mean
        log_peak_ratio = np.log(spectral_peak_ratio + 1)
        log_peak_ratio_scaled = (log_peak_ratio - 6.0) / 2.5

        return np.array(
            [env_var_scaled, inst_freq_var_scaled, log_peak_ratio_scaled],
            dtype=np.float32,
        )


class ToyModulationClassifier(nn.Module):
    """A tiny PyTorch classifier for modulation type classification."""

    def __init__(self, weights: np.ndarray, biases: np.ndarray):
        """
        Initialize the classifier with pretrained weights.

        Args:
            weights: Weight matrix of shape (num_classes, num_features)
            biases: Bias vector of shape (num_classes,)
        """
        super().__init__()
        self.linear = nn.Linear(weights.shape[1], weights.shape[0])

        # Load pretrained weights
        with torch.no_grad():
            self.linear.weight.copy_(torch.from_numpy(weights))
            self.linear.bias.copy_(torch.from_numpy(biases))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the classifier."""
        return self.linear(x)

    def predict(self, features: np.ndarray) -> int:
        """
        Predict the modulation type from features.

        Args:
            features: Feature array of shape (num_features,)

        Returns:
            Predicted class index
        """
        self.eval()
        with torch.no_grad():
            x = torch.from_numpy(features).unsqueeze(0)
            logits = self.forward(x)
            return int(torch.argmax(logits, dim=1).item())


class TestToyModulationClassifier(TestCase):
    """Test cases for the toy modulation classifier."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        # Fixed seed for reproducibility
        cls.seed = 42
        torch.manual_seed(cls.seed)

        # Initialize signal generator and feature extractor
        cls.generator = SyntheticSignalGenerator(seed=cls.seed)
        cls.extractor = FeatureExtractor()

        # Load the pretrained model
        cls.model = ToyModulationClassifier(W, b)

    def test_am_classification(self):
        """Test that AM signal is correctly classified."""
        signal = self.generator.generate_am()
        features = self.extractor.extract_features(signal)
        prediction = self.model.predict(features)
        predicted_label = LABELS[prediction]

        self.assertEqual(
            predicted_label,
            "AM",
            f"Expected AM, got {predicted_label}. Features: {features}",
        )

    def test_fm_classification(self):
        """Test that FM signal is correctly classified."""
        signal = self.generator.generate_fm()
        features = self.extractor.extract_features(signal)
        prediction = self.model.predict(features)
        predicted_label = LABELS[prediction]

        self.assertEqual(
            predicted_label,
            "FM",
            f"Expected FM, got {predicted_label}. Features: {features}",
        )

    def test_cw_classification(self):
        """Test that CW signal is correctly classified."""
        signal = self.generator.generate_cw()
        features = self.extractor.extract_features(signal)
        prediction = self.model.predict(features)
        predicted_label = LABELS[prediction]

        self.assertEqual(
            predicted_label,
            "CW",
            f"Expected CW, got {predicted_label}. Features: {features}",
        )

    def test_ssb_classification(self):
        """Test that SSB signal is correctly classified."""
        signal = self.generator.generate_ssb()
        features = self.extractor.extract_features(signal)
        prediction = self.model.predict(features)
        predicted_label = LABELS[prediction]

        self.assertEqual(
            predicted_label,
            "SSB",
            f"Expected SSB, got {predicted_label}. Features: {features}",
        )

    def test_model_output_shape(self):
        """Test that model output has correct shape."""
        features = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        x = torch.from_numpy(features).unsqueeze(0)

        self.model.eval()
        with torch.no_grad():
            output = self.model(x)

        self.assertEqual(output.shape, (1, 4), "Expected output shape (1, 4)")

    def test_deterministic_predictions(self):
        """Test that predictions are deterministic with same seed."""
        # Reset generator with same seed
        generator1 = SyntheticSignalGenerator(seed=self.seed)
        generator2 = SyntheticSignalGenerator(seed=self.seed)

        signal1 = generator1.generate_am()
        signal2 = generator2.generate_am()

        features1 = self.extractor.extract_features(signal1)
        features2 = self.extractor.extract_features(signal2)

        np.testing.assert_array_almost_equal(
            features1, features2, err_msg="Features should be deterministic"
        )

        pred1 = self.model.predict(features1)
        pred2 = self.model.predict(features2)

        self.assertEqual(pred1, pred2, "Predictions should be deterministic")

    def test_labels_match_weights_shape(self):
        """Test that number of labels matches model output dimension."""
        self.assertEqual(
            len(LABELS),
            W.shape[0],
            "Number of labels should match weight matrix rows",
        )

    def test_feature_count_matches_weights(self):
        """Test that feature dimension matches model input dimension."""
        signal = self.generator.generate_am()
        features = self.extractor.extract_features(signal)

        self.assertEqual(
            len(features),
            W.shape[1],
            "Feature count should match weight matrix columns",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
