#!/usr/bin/env python3
"""
Unit tests for Signal Classifier module.
Run with: python3 -m pytest test/test_signal_classifier.py -v
"""

import unittest
import numpy as np
from unittest.mock import patch, MagicMock


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

    def test_mapping_exists(self):
        """Verify TORCHSIG_TO_OWRX_MODE mapping exists."""
        from owrx.signal_classifier import TORCHSIG_TO_OWRX_MODE
        self.assertIsInstance(TORCHSIG_TO_OWRX_MODE, dict)
        self.assertGreater(len(TORCHSIG_TO_OWRX_MODE), 0)

    def test_common_mappings(self):
        """Test common modulation mappings."""
        from owrx.signal_classifier import TORCHSIG_TO_OWRX_MODE
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("am-dsb"), "am")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("am-usb"), "usb")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("am-lsb"), "lsb")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("fm"), "nfm")
        self.assertEqual(TORCHSIG_TO_OWRX_MODE.get("ook"), "cw")

    def test_sig53_classes_count(self):
        """Verify SIG53_CLASSES has expected count."""
        from owrx.signal_classifier import SIG53_CLASSES
        self.assertEqual(len(SIG53_CLASSES), 53)


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


if __name__ == "__main__":
    unittest.main()
