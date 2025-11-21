# Signal Classifier Testing Guide

This document describes how to test the TorchSig signal classifier implementation in OpenWebRX+.

## Test Environment

- **Branch**: `claude/add-signal-classification-plugin-01CgkoxUvr1Z889pjJEoPvBC`
- **Date**: November 2025
- **Dependencies**: torch, torchsig, numpy

## Automated Tests

### 1. Unit Tests

Create `test/test_signal_classifier.py`:

```python
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

    @patch("owrx.feature.FeatureDetector.has_torchsig", return_value=True)
    def test_is_available_when_installed(self, mock_has):
        """Test is_available returns True when TorchSig installed."""
        from owrx.signal_classifier import is_available
        # Note: This may still return False if actual import fails
        # Use mock to isolate the test
        from owrx.feature import FeatureDetector
        fd = FeatureDetector()
        self.assertTrue(fd.is_available("signal_classifier"))


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
        """Test model initial state."""
        from owrx.signal_classifier import SignalClassifierModel
        # Reset singleton for clean test
        SignalClassifierModel._instance = None
        model = SignalClassifierModel.getInstance()
        self.assertFalse(model.loaded)
        self.assertIsNone(model.model)


class TestClassification(unittest.TestCase):
    """Test classification functionality (requires TorchSig)."""

    @unittest.skipUnless(
        __import__("importlib.util").util.find_spec("torchsig"),
        "TorchSig not installed"
    )
    def test_classify_synthetic_signal(self):
        """Test classification with synthetic AM signal."""
        from owrx.signal_classifier import SignalClassifierModel

        # Reset and load model
        SignalClassifierModel._instance = None
        model = SignalClassifierModel.getInstance()

        if not model.load("cpu"):
            self.skipTest(f"Model failed to load: {model.load_error}")

        # Generate synthetic AM carrier
        t = np.linspace(0, 1, 48000)
        signal = np.exp(2j * np.pi * 1000 * t).astype(np.complex64)

        predictions = model.classify(signal, top_k=3)

        self.assertIsInstance(predictions, list)
        self.assertGreater(len(predictions), 0)
        self.assertIn("torchsig_class", predictions[0])
        self.assertIn("confidence", predictions[0])
        self.assertIn("mode", predictions[0])


if __name__ == "__main__":
    unittest.main()
```

### 2. Run Automated Tests

```bash
# Run all signal classifier tests
python3 -m pytest test/test_signal_classifier.py -v

# Run with coverage
python3 -m pytest test/test_signal_classifier.py -v --cov=owrx.signal_classifier

# Run specific test class
python3 -m pytest test/test_signal_classifier.py::TestFeatureDetection -v
```

### 3. Integration Test Script

Create `test/test_classifier_integration.py`:

```python
#!/usr/bin/env python3
"""
Integration test for signal classifier.
Tests the full pipeline without requiring SDR hardware.
"""

import sys
import json
import numpy as np


def test_feature_detection():
    """Test 1: Feature detection."""
    print("Test 1: Feature Detection")
    from owrx.feature import FeatureDetector
    fd = FeatureDetector()

    available = fd.is_available("signal_classifier")
    print(f"  signal_classifier available: {available}")

    if not available:
        failed = fd.get_failed_requirements("signal_classifier")
        print(f"  Failed requirements: {failed}")

    return available


def test_config():
    """Test 2: Configuration."""
    print("\nTest 2: Configuration")
    from owrx.signal_classifier import get_config

    config = get_config()
    print(f"  enabled: {config['enabled']}")
    print(f"  threshold: {config['threshold']}")
    print(f"  interval: {config['interval']}")
    print(f"  device: {config['device']}")

    return True


def test_model_loading():
    """Test 3: Model loading."""
    print("\nTest 3: Model Loading")

    try:
        from owrx.signal_classifier import SignalClassifierModel
        SignalClassifierModel._instance = None  # Reset singleton
        model = SignalClassifierModel.getInstance()

        success = model.load("cpu")
        print(f"  Model loaded: {success}")

        if not success:
            print(f"  Error: {model.load_error}")

        return success
    except ImportError as e:
        print(f"  Import error: {e}")
        return False


def test_classification():
    """Test 4: Classification."""
    print("\nTest 4: Classification")

    try:
        from owrx.signal_classifier import SignalClassifierModel
        model = SignalClassifierModel.getInstance()

        if not model.loaded:
            print("  Skipped: Model not loaded")
            return None

        # Generate test signals
        t = np.linspace(0, 1, 48000, dtype=np.float32)

        # AM-like signal
        am_signal = (1 + 0.5 * np.sin(2 * np.pi * 100 * t)) * np.exp(2j * np.pi * 1000 * t)
        am_signal = am_signal.astype(np.complex64)

        predictions = model.classify(am_signal, top_k=3)

        print(f"  Predictions for AM-like signal:")
        for p in predictions:
            mode = p['mode'] or p['torchsig_class']
            print(f"    {mode}: {p['confidence']:.1%}")

        return len(predictions) > 0
    except Exception as e:
        print(f"  Error: {e}")
        return False


def test_output_format():
    """Test 5: Output format."""
    print("\nTest 5: Output Format")

    try:
        from owrx.signal_classifier import SignalClassifierModel
        model = SignalClassifierModel.getInstance()

        if not model.loaded:
            print("  Skipped: Model not loaded")
            return None

        t = np.linspace(0, 1, 48000, dtype=np.float32)
        signal = np.exp(2j * np.pi * 1000 * t).astype(np.complex64)

        predictions = model.classify(signal, top_k=3)

        # Verify JSON serializable
        output = {
            "timestamp": 1700000000000,
            "freq": 14074000,
            "predictions": predictions,
            "sample_rate": 48000
        }

        json_str = json.dumps(output)
        parsed = json.loads(json_str)

        print(f"  JSON output valid: True")
        print(f"  Sample: {json_str[:100]}...")

        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Signal Classifier Integration Tests")
    print("=" * 60)

    results = {
        "Feature Detection": test_feature_detection(),
        "Configuration": test_config(),
        "Model Loading": test_model_loading(),
        "Classification": test_classification(),
        "Output Format": test_output_format(),
    }

    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for test, result in results.items():
        if result is True:
            status = "PASS"
            passed += 1
        elif result is False:
            status = "FAIL"
            failed += 1
        else:
            status = "SKIP"
            skipped += 1
        print(f"  {test}: {status}")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

Run with:
```bash
python3 test/test_classifier_integration.py
```

## Manual Tests

### 1. Feature Detection Check

```bash
# Check feature report
python3 -m owrx.feature 2>/dev/null | grep -A10 signal_classifier
```

Expected output:
```
signal_classifier:
  available: true
  requirements:
    torchsig:
      available: true
      enabled: true
      description: OpenWebRX can use TorchSig for automatic signal classification...
```

### 2. Web Interface Tests

1. **Settings Page**
   - Navigate to Settings > Demodulation and decoding
   - Verify "Signal classifier" section appears
   - Enable the classifier
   - Save settings

2. **Classification Panel**
   - Open main receiver page
   - Tune to a known signal
   - Verify classification panel appears (if enabled)
   - Check predictions update periodically

3. **Browser Console**
   ```javascript
   // Open browser developer tools, watch for:
   // Network tab: WebSocket messages with type "classification"
   ```

### 3. WebSocket Message Test

With OpenWebRX+ running:

```python
#!/usr/bin/env python3
"""Test WebSocket classification messages."""
import websocket
import json

def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get("type") == "classification":
            print("Classification received:", json.dumps(data, indent=2))
    except:
        pass

ws = websocket.WebSocketApp(
    "ws://localhost:8073/ws/",
    on_message=on_message
)
ws.run_forever()
```

## Testing Checklist

### Installation Verification
- [ ] `pip install torch torchsig numpy` succeeds
- [ ] `python3 -c "import torchsig"` works
- [ ] Feature report shows signal_classifier available

### Configuration
- [ ] Settings section appears in web interface
- [ ] Can enable/disable classifier
- [ ] Can change threshold value
- [ ] Can change interval value
- [ ] Can switch between CPU/CUDA

### Runtime Behavior
- [ ] Classifier starts when enabled
- [ ] Classification panel appears in UI
- [ ] Predictions update at configured interval
- [ ] Confidence bars display correctly
- [ ] No errors in browser console
- [ ] No errors in server logs

### Performance
- [ ] Audio playback unaffected
- [ ] Waterfall display smooth
- [ ] CPU usage acceptable
- [ ] Memory usage stable

## Using TorchSig for Synthetic Test Signals

TorchSig can generate synthetic signals for all 53 modulation classes, providing better test coverage than simple numpy-generated signals.

### Signal Generation Example

```python
from torchsig.signals import PSKSignal, FSKSignal, AMSignal, OFDMSignal
from torchsig.utils.types import SignalDescription
import numpy as np

def generate_test_signal(modulation: str, num_samples: int = 4096):
    """Generate synthetic signal for testing."""
    signal_desc = SignalDescription(sample_rate=1.0, num_iq_samples=num_samples)

    if modulation == "qpsk":
        signal_gen = PSKSignal(order=4)
    elif modulation == "4fsk":
        signal_gen = FSKSignal(order=4)
    elif modulation == "am":
        signal_gen = AMSignal()
    elif modulation == "ofdm-64":
        signal_gen = OFDMSignal(num_subcarriers=64)
    else:
        raise ValueError(f"Unknown modulation: {modulation}")

    iq_data = signal_gen(signal_desc)
    return iq_data.astype(np.complex64)

# Generate and classify
signal = generate_test_signal("qpsk", 4096)
predictions = model.classify(signal, top_k=3)
```

### Available Signal Generators

| Generator | Modulations |
|-----------|-------------|
| `PSKSignal(order=N)` | BPSK (2), QPSK (4), 8PSK (8), etc. |
| `FSKSignal(order=N)` | 2FSK, 4FSK, 8FSK, etc. |
| `QAMSignal(order=N)` | 16QAM, 64QAM, 256QAM, etc. |
| `OOKSignal()` | On-Off Keying (CW-like) |
| `AMSignal()` | Amplitude Modulation |
| `FMSignal()` | Frequency Modulation |
| `OFDMSignal(num_subcarriers=N)` | OFDM variants |

### Benefits of Synthetic Testing

1. **Reproducible**: Same parameters produce identical signals
2. **Ground Truth**: Known modulation type for accuracy testing
3. **No Hardware**: Tests run without SDR equipment
4. **CI/CD Compatible**: Automated testing in pipelines
5. **Edge Cases**: Generate specific SNR, bandwidth, impairments

## Known Limitations

1. **Model Accuracy**: TorchSig models trained on synthetic data; real-world accuracy varies
2. **First Classification**: Initial classification slow due to lazy model loading
3. **Sample Rate**: Best results at 48kHz; other rates may affect accuracy
4. **Bandwidth**: Classifier sees filtered passband, not full spectrum

## Troubleshooting Failed Tests

### Feature detection fails
```bash
# Check Python path
python3 -c "import sys; print(sys.path)"

# Check torchsig installation
pip show torchsig
```

### Model loading fails
```bash
# Check for model download issues
python3 -c "
from torchsig.models import efficientnet_b0
model = efficientnet_b0(pretrained=True, num_classes=53)
print('Success')
"
```

### Classification returns empty
- Check signal strength
- Verify sample rate matches expectation
- Try lowering confidence threshold
