# Signal Classifier Design Document

## Overview

The Signal Classifier plugin integrates TorchSig's deep learning-based signal classification into OpenWebRX+. It analyzes IQ samples in real-time and predicts the modulation type of the currently tuned signal.

## Architecture

### Components

1. **SignalClassifierModel** (`owrx/signal_classifier.py`)
   - Singleton wrapper for TorchSig model
   - Handles lazy loading and caching
   - Thread-safe model access

2. **SignalClassifier** (`owrx/signal_classifier.py`)
   - ThreadModule-based signal processor
   - Receives IQ samples from selector buffer
   - Outputs JSON predictions

3. **Feature Detection** (`owrx/feature.py`)
   - `has_torchsig()` method checks for TorchSig availability
   - Added to features registry

4. **DSP Integration** (`owrx/dsp.py`)
   - Classifier chain in `ClientDemodulatorChain`
   - Parallel branch from selector buffer
   - JSON output wiring

5. **Frontend** (`htdocs/`)
   - Classification panel in index.html
   - JavaScript handler in openwebrx.js
   - CSS styles in openwebrx.css

### Data Flow

```
SDR Source
    │
    ▼
Selector (bandwidth filtering)
    │
    ├─────────────────────────────┐
    │                             │
    ▼                             ▼
Demodulator                  SignalClassifier
    │                             │
    ▼                             ▼
ClientAudioChain              JSON Output
    │                             │
    ▼                             ▼
WebSocket (audio)            WebSocket (classification)
    │                             │
    ▼                             ▼
Browser Audio                UI Panel
```

## Implementation Details

### Model Loading

```python
class SignalClassifierModel:
    # Singleton pattern ensures single model instance
    _instance = None
    _lock = threading.Lock()

    def load(self, device="cpu"):
        # Lazy loading - only load when first needed
        from torchsig.models import efficientnet_b0
        self.model = efficientnet_b0(pretrained=True, num_classes=53)
```

### Sample Processing

```python
class SignalClassifier(ThreadModule):
    def run(self):
        while self.doRun:
            data = self.reader.read()
            samples = np.frombuffer(data, dtype=np.complex64)
            self.buffer.extend(samples)

            if len(self.buffer) >= self.buffer_size:
                predictions = self.model.classify(samples)
                # Output as JSON
```

### Classification Mapping

TorchSig classes are mapped to OpenWebRX+ modes via `TORCHSIG_TO_OWRX_MODE` dictionary:

```python
TORCHSIG_TO_OWRX_MODE = {
    "am-dsb": "am",
    "am-usb": "usb",
    "fm": "nfm",
    "ook": "cw",
    # ...
}
```

## Configuration

Settings stored in OpenWebRX+ config:

```python
signal_classifier_enabled = False    # Enable/disable
signal_classifier_threshold = 0.5   # Confidence threshold
signal_classifier_interval = 1.0    # Seconds between classifications
signal_classifier_device = "cpu"    # or "cuda" for GPU
```

## Output Format

```json
{
  "timestamp": 1700000000000,
  "freq": 14074000,
  "predictions": [
    {"torchsig_class": "am-usb", "confidence": 0.87, "mode": "usb"},
    {"torchsig_class": "bpsk", "confidence": 0.08, "mode": "bpsk31"}
  ],
  "sample_rate": 48000
}
```

## Files Modified/Added

### New Files
- `owrx/signal_classifier.py` - Main classifier module
- `docs/signal-classifier/README.md` - User documentation
- `docs/signal-classifier/signal-classifier-design.md` - This file

### Modified Files
- `owrx/feature.py` - Added torchsig feature detection
- `owrx/config/defaults.py` - Added default configuration
- `owrx/controllers/settings/decoding.py` - Added settings UI
- `owrx/dsp.py` - Integrated classifier chain
- `owrx/connection.py` - Added write_classification method
- `htdocs/index.html` - Added classification panel
- `htdocs/openwebrx.js` - Added message handler
- `htdocs/css/openwebrx.css` - Added panel styles

## Future Enhancements

1. **Auto-mode selection** - Automatically switch to predicted mode
2. **Waterfall annotations** - Show classifications on waterfall
3. **Confidence history** - Track classification changes over time
4. **Custom model support** - Allow user-trained models
5. **Multi-signal detection** - Classify multiple signals in passband
