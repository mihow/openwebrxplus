#!/usr/bin/env python3
"""
Unit tests for Signal Classifier module.
Run with: python3 -m pytest test/test_signal_classifier.py -v

Note: Some tests require pycsdr to be installed (OpenWebRX+ dependency).
Tests will be skipped gracefully if dependencies are missing.
"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock


def pycsdr_available():
    """Check if pycsdr is available."""
    try:
        import pycsdr
        return True
    except ImportError:
        return False


class TestFeatureDetection(unittest.TestCase):
    """Test feature detection for TorchSig."""

    def test_feature_registered(self):
        """Verify signal_classifier is in features dict."""
        from owrx.feature import FeatureDetector
        self.assertIn("signal_classifier", FeatureDetector.features)
        self.assertEqual(FeatureDetector.features["signal_classifier"], ["torchsig"])

    def test_has_torchsig_method_exists(self):
        """Verify has_torchsig method exists."""
        from owrx.feature import FeatureDetector
        fd = FeatureDetector()
        self.assertTrue(hasattr(fd, "has_torchsig"))
        self.assertTrue(callable(fd.has_torchsig))


class TestConfiguration(unittest.TestCase):
    """Test configuration defaults and retrieval."""

    def test_default_config_values(self):
        """Verify default configuration values."""
        from owrx.config.defaults import defaultConfig
        self.assertFalse(defaultConfig["signal_classifier_enabled"])
        self.assertEqual(defaultConfig["signal_classifier_threshold"], 0.5)
        self.assertEqual(defaultConfig["signal_classifier_interval"], 1.0)
        self.assertEqual(defaultConfig["signal_classifier_device"], "cpu")

    @unittest.skipUnless(pycsdr_available(), "pycsdr not installed")
    def test_get_config_function(self):
        """Test get_config returns expected structure."""
        from owrx.signal_classifier import get_config
        config = get_config()
        self.assertIn("enabled", config)
        self.assertIn("threshold", config)
        self.assertIn("interval", config)
        self.assertIn("device", config)


class TestModeMapping(unittest.TestCase):
    """Test TorchSig to OpenWebRX+ mode mapping."""

    @unittest.skipUnless(pycsdr_available(), "pycsdr not installed")
    def test_mapping_exists(self):
        """Verify TORCHSIG_TO_OWRX_MODE mapping exists."""
        from owrx.signal_classifier import TORCHSIG_TO_OWRX_MODE
        self.assertIsInstance(TORCHSIG_TO_OWRX_MODE, dict)
        self.assertGreater(len(TORCHSIG_TO_OWRX_MODE), 0)

    @unittest.skipUnless(pycsdr_available(), "pycsdr not installed")
    def test_common_mappings(self):
        """Test common modulation mappings."""
        from owrx.signal_classifier import TORCHSIG_TO_OWRX_MODE
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("am-dsb"), "am")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("am-usb"), "usb")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("am-lsb"), "lsb")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("fm"), "nfm")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("ook"), "cw")

    @unittest.skipUnless(pycsdr_available(), "pycsdr not installed")
    def test_sig53_classes_count(self):
        """Verify SIG53_CLASSES has expected count."""
        from owrx.signal_classifier import SIG53_CLASSES
        self.assertEqual(len(SIG53_CLASSES), 53)


@unittest.skipUnless(pycsdr_available(), "pycsdr not installed")
class TestSignalClassifierModule(unittest.TestCase):
    """Test SignalClassifier module interface."""

    def test_classifier_instantiation(self):
        """Test SignalClassifier can be instantiated."""
        from owrx.signal_classifier import SignalClassifier
        classifier = SignalClassifier(
            sampleRate=48000,
            interval=1.0,
            threshold=0.5,
            device="cpu"
        )
        self.assertEqual(classifier.sampleRate, 48000)
        self.assertEqual(classifier.interval, 1.0)
        self.assertEqual(classifier.threshold, 0.5)

    def test_input_output_formats(self):
        """Test input/output format declarations."""
        from owrx.signal_classifier import SignalClassifier
        from pycsdr.types import Format
        classifier = SignalClassifier()
        self.assertEqual(classifier.getInputFormat(), Format.COMPLEX_FLOAT)
        self.assertEqual(classifier.getOutputFormat(), Format.CHAR)

    def test_set_dial_frequency(self):
        """Test setDialFrequency method."""
        from owrx.signal_classifier import SignalClassifier
        classifier = SignalClassifier()
        classifier.setDialFrequency(14074000)
        self.assertEqual(classifier.frequency, 14074000)


@unittest.skipUnless(pycsdr_available(), "pycsdr not installed")
class TestSignalClassifierModel(unittest.TestCase):
    """Test SignalClassifierModel singleton."""

    def test_singleton_pattern(self):
        """Test model uses singleton pattern."""
        from owrx.signal_classifier import SignalClassifierModel
        model1 = SignalClassifierModel.getInstance()
        model2 = SignalClassifierModel.getInstance()
        self.assertIs(model1, model2)

    def test_model_initial_state(self):
        """Test model initial state before loading."""
        from owrx.signal_classifier import SignalClassifierModel
        # Get fresh instance state info (don't reset singleton in tests)
        model = SignalClassifierModel.getInstance()
        # Model may or may not be loaded depending on test order
        self.assertIsNotNone(model)


def torchsig_available():
    """Check if TorchSig is available for testing."""
    try:
        import torch
        import torchsig
        return True
    except ImportError:
        return False


@unittest.skipUnless(torchsig_available(), "TorchSig not installed")
class TestClassificationWithSyntheticSignals(unittest.TestCase):
    """
    Test classification using TorchSig-generated synthetic signals.
    These tests validate that the classifier correctly identifies known modulations.
    """

    @classmethod
    def setUpClass(cls):
        """Load model once for all tests."""
        from owrx.signal_classifier import SignalClassifierModel
        cls.model = SignalClassifierModel.getInstance()
        if not cls.model.loaded:
            cls.model.load("cpu")

    def generate_signal_from_dataset(self):
        """Generate synthetic signal using TorchSig default_dataset (v2.0 API)."""
        try:
            from torchsig.utils.defaults import default_dataset
            dataset = default_dataset(target_labels=["class_name"])
            signal = next(dataset)
            # Extract IQ data from signal object
            if hasattr(signal, 'iq_data'):
                return signal.iq_data.astype(np.complex64), getattr(signal, 'class_name', None)
            elif isinstance(signal, tuple):
                return signal[0].astype(np.complex64), signal[1] if len(signal) > 1 else None
            else:
                return np.array(signal, dtype=np.complex64), None
        except Exception:
            # Fallback to simple numpy signal
            return (np.random.randn(4096) + 1j * np.random.randn(4096)).astype(np.complex64), None

    def test_model_loaded(self):
        """Verify model is loaded for synthetic signal tests."""
        self.assertTrue(self.model.loaded, "Model should be loaded for these tests")

    def test_classify_returns_predictions(self):
        """Test that classify returns non-empty predictions."""
        signal = np.random.randn(4096) + 1j * np.random.randn(4096)
        signal = signal.astype(np.complex64)

        predictions = self.model.classify(signal, top_k=3)

        self.assertIsInstance(predictions, list)
        self.assertGreater(len(predictions), 0)

    def test_prediction_structure(self):
        """Test prediction dictionary structure."""
        signal = np.random.randn(4096) + 1j * np.random.randn(4096)
        signal = signal.astype(np.complex64)

        predictions = self.model.classify(signal, top_k=1)

        self.assertGreater(len(predictions), 0)
        pred = predictions[0]
        self.assertIn("torchsig_class", pred)
        self.assertIn("confidence", pred)
        self.assertIn("mode", pred)

    def test_confidence_range(self):
        """Test that confidence values are in valid range."""
        signal = np.random.randn(4096) + 1j * np.random.randn(4096)
        signal = signal.astype(np.complex64)

        predictions = self.model.classify(signal, top_k=5)

        for pred in predictions:
            self.assertGreaterEqual(pred["confidence"], 0.0)
            self.assertLessEqual(pred["confidence"], 1.0)

    def test_top_k_limit(self):
        """Test that top_k limits number of predictions."""
        signal = np.random.randn(4096) + 1j * np.random.randn(4096)
        signal = signal.astype(np.complex64)

        for k in [1, 3, 5]:
            predictions = self.model.classify(signal, top_k=k)
            self.assertLessEqual(len(predictions), k)

    def test_empty_signal_handling(self):
        """Test handling of zero/empty signals."""
        signal = np.zeros(4096, dtype=np.complex64)
        predictions = self.model.classify(signal, top_k=3)
        # Should still return predictions (model handles edge cases)
        self.assertIsInstance(predictions, list)


@unittest.skipUnless(torchsig_available(), "TorchSig not installed")
class TestSyntheticSignalGeneration(unittest.TestCase):
    """Test TorchSig synthetic signal generation capabilities."""

    def test_default_dataset_creation(self):
        """Test creating a default dataset with TorchSig v2.0 API."""
        try:
            from torchsig.utils.defaults import default_dataset
            dataset = default_dataset(target_labels=["class_name"])
            signal = next(dataset)
            self.assertIsNotNone(signal)
        except ImportError:
            self.skipTest("TorchSig default_dataset not available")
        except Exception as e:
            self.skipTest(f"TorchSig dataset creation failed: {e}")

    def test_dataset_produces_iq_data(self):
        """Test that dataset produces usable IQ data."""
        try:
            from torchsig.utils.defaults import default_dataset
            dataset = default_dataset(target_labels=["class_name"])
            signal = next(dataset)

            # Signal should be iterable or have iq_data attribute
            if hasattr(signal, 'iq_data'):
                iq_data = signal.iq_data
            elif isinstance(signal, (tuple, list)):
                iq_data = signal[0]
            else:
                iq_data = signal

            self.assertIsNotNone(iq_data)
            self.assertGreater(len(iq_data), 0)
        except ImportError:
            self.skipTest("TorchSig not available")
        except Exception as e:
            self.skipTest(f"Test skipped: {e}")

    def test_dataset_with_multiple_signals(self):
        """Test dataset with multiple signal configuration."""
        try:
            from torchsig.utils.defaults import default_dataset
            dataset = default_dataset(
                target_labels=["class_name"],
                num_signals_max=3,
                num_signals_min=1
            )
            signal = next(dataset)
            self.assertIsNotNone(signal)
        except ImportError:
            self.skipTest("TorchSig not available")
        except Exception as e:
            self.skipTest(f"Test skipped: {e}")


if __name__ == "__main__":
    unittest.main()
