# ONNX Signal Classifier Implementation Guide

## Overview

This guide documents the migration from TorchSig 2.0 (XCiT1d, no pretrained weights) to TorchSig 1.1.0 EfficientNet-B0 (pretrained on Sig53) exported to ONNX format for production use.

## Why This Approach?

### The Problem with TorchSig 2.0
- ❌ XCiT1d model has **no pretrained weights**
- ❌ Produces **random predictions** until trained
- ❌ Would require **days of GPU training** on Sig53 dataset
- ❌ Requires **3.7 GB** of PyTorch dependencies

### The Solution: TorchSig 1.1.0 + ONNX
- ✅ EfficientNet-B0 with **pretrained Sig53 weights** (62.75% accuracy)
- ✅ **Works immediately** with real predictions
- ✅ **20 MB** ONNX Runtime (vs 3.7 GB PyTorch)
- ✅ **98% smaller** Docker image
- ✅ **Faster inference** and lower memory usage

## Architecture Overview

### Current (TorchSig 2.0)
```
IQ Samples → PyTorch (3.7 GB) → XCiT1d (untrained) → Random Predictions
```

### New (ONNX)
```
IQ Samples → ONNX Runtime (20 MB) → EfficientNet-B0 (pretrained) → Real Predictions
```

## Implementation Phases

### Phase 1: Model Export (One-Time)
**Goal:** Export TorchSig 1.1.0 EfficientNet-B0 to ONNX format

**Key Points:**
- Requires PyTorch/TorchSig temporarily (only for export)
- Creates a ~30-50 MB `.onnx` file with embedded weights
- Only needs to be done once per model version
- Can be done on any machine (dev machine, CI/CD, etc.)

**Dependencies:**
```bash
pip install torch==1.13.1 onnx onnxruntime
pip install https://github.com/TorchDSP/torchsig/archive/refs/tags/v1.1.0.tar.gz
```

**Export Script:** `export_torchsig_to_onnx.py`

**Output:** `torchsig_efficientnet_b0_sig53.onnx` (~30-50 MB)

---

### Phase 2: Docker Integration
**Goal:** Update Dockerfile to use ONNX Runtime instead of PyTorch

**Key Changes:**
- Remove PyTorch (torch, torchvision, torchaudio) - **saves 3.5 GB**
- Remove TorchSig - **saves 200 MB**
- Add ONNX Runtime - **adds 20 MB**
- Copy pre-exported ONNX model to `/usr/share/openwebrx/models/`

**File:** `Dockerfile.dev`

**Size Impact:**
- Before: +3.7 GB
- After: +70 MB (model + runtime)
- **Savings: 3.63 GB**

---

### Phase 3: Code Migration
**Goal:** Update signal_classifier.py to use ONNX Runtime

**Key Changes:**

#### Model Loading
```python
# OLD (TorchSig 2.0)
from torchsig.models import XCiT1d
model = XCiT1d(...)  # No pretrained weights

# NEW (ONNX)
import onnxruntime as ort
session = ort.InferenceSession("model.onnx")
```

#### Input Format
```python
# OLD (XCiT1d - channels first)
iq_tensor = torch.zeros(1, 2, len(samples))  # (batch, channels, length)
iq_tensor[0, 0, :] = real
iq_tensor[0, 1, :] = imag

# NEW (ONNX - complex tensor)
iq_numpy = np.expand_dims(samples, axis=0)  # (batch, length)
```

#### Inference
```python
# OLD (PyTorch)
with torch.no_grad():
    output = model(iq_tensor)
    probs = torch.softmax(output, dim=-1)

# NEW (ONNX)
outputs = session.run(None, {'iq_samples': iq_numpy})
probs = softmax(outputs[0])
```

**File:** `owrx/signal_classifier.py`

---

### Phase 4: Testing
**Goal:** Verify ONNX classifier produces correct predictions

**Test Signals:**
- FM broadcast (should detect: `fm` or `wfm`)
- RTTY (should detect: `2fsk`)
- FT8 (should detect: `ofdm-64`)
- DMR (should detect: `4gfsk`)
- CW (should detect: `ook`)

**Validation:**
- Check predictions are not random
- Verify confidence scores make sense (higher for clean signals)
- Compare with known signal types

---

### Phase 5: Documentation
**Goal:** Update user-facing docs to explain ONNX approach

**Files to Update:**
- `README.md` - Add ONNX benefits
- `INSTALLATION.md` - Update dependencies
- Settings page help text - Explain pretrained model

---

## Key Technical Decisions

### Why TorchSig 1.1.0 instead of 2.0?
**TorchSig 1.1.0:**
- ✅ Has pretrained EfficientNet-B0 weights
- ✅ Proven 62.75% accuracy on Sig53
- ✅ Ready to use immediately

**TorchSig 2.0:**
- ❌ No pretrained weights for XCiT1d
- ❌ Random predictions until trained
- ❌ Would need Sig53 dataset + GPU + days

### Why ONNX instead of PyTorch?
**Production Use Case:**
- We're doing **inference only** (no training)
- We have a **pretrained model**
- We want **small Docker images**

**ONNX Benefits:**
- 98% smaller (20 MB vs 3.7 GB)
- Faster inference (optimized for production)
- No Python version conflicts
- Cross-platform compatible

**PyTorch Use Case:**
- Training models
- Fine-tuning
- Research/experimentation
- Using TorchSig's data generation

### Input Buffer Size
**Decision:** Use 4096 samples

**Rationale:**
- EfficientNet-B0 was likely trained on fixed-size inputs
- Common sizes: 1024, 2048, 4096, 8192
- 4096 provides good balance:
  - At 48 kHz: ~85ms of signal
  - At 200 kHz: ~20ms of signal
  - Enough for most modulation detection

**Adjustable:** Can change `buffer_size` in `__init__()` if needed

### Classification Interval
**Decision:** Default 1.0 second

**Rationale:**
- Balance between responsiveness and CPU usage
- Signals don't change mode rapidly
- User can adjust in settings (0.1 to 60.0 seconds)

---

## Sig53 Dataset Classes

The model is trained to recognize **53 modulation types:**

### Analog (7)
- `ook` → CW
- `am-dsb`, `am-dsb-sc` → AM
- `am-lsb` → LSB
- `am-usb` → USB
- `fm` → NFM
- `wbfm` → WFM
- `lfm` → (no mapping)

### PSK (9)
- `bpsk` → BPSK31
- `qpsk`, `8psk`, `16psk`, `32psk`, `64psk` → (no mapping)

### QAM (7)
- `16qam` through `1024qam` → (no mapping)

### FSK/GFSK/MSK (17)
- `2fsk` → RTTY170
- `4fsk`, `4gfsk` → DMR
- `gmsk` → D-Star
- Others → (no mapping)

### OFDM (12)
- `ofdm-64` → FT8
- `ofdm-2048` → DAB
- Others → (no mapping)

### Other
- `4ask`, `8ask`, `chirp_ss`, etc.

**Unmapped classes:** Set to `null` in predictions (still shown with confidence)

---

## Performance Expectations

### Model Accuracy
- **Clean signals (>20dB SNR):** ~85-90% accuracy
- **Moderate impairment (10dB SNR):** ~70-80% accuracy
- **Heavy impairment (<0dB SNR):** ~50-60% accuracy
- **Overall Sig53 test:** 62.75% accuracy

### Inference Speed
- **CPU:** ~30-50ms per classification
- **CUDA GPU:** ~5-10ms per classification

### Memory Usage
- **Model size:** 30-50 MB
- **Runtime memory:** ~100-150 MB
- **PyTorch (for comparison):** ~800 MB

---

## Troubleshooting

### Issue: Model predictions are all the same class
**Cause:** Model not loaded or using wrong input format
**Solution:** Check logs for model loading errors, verify input tensor shape

### Issue: Confidence scores all near 0.0 or 1.0
**Cause:** Missing softmax on output logits
**Solution:** Verify softmax is applied to raw model outputs

### Issue: "Input shape mismatch"
**Cause:** Buffer size doesn't match model's expected input
**Solution:** Adjust `buffer_size` to 1024, 2048, 4096, or 8192

### Issue: Very low accuracy on real signals
**Cause:** Model expects different sample rate or normalization
**Solution:**
- Verify samples are normalized to [-1, 1]
- Check if resampling is needed
- Try different buffer sizes

---

## Future Improvements

### Short-term
- [ ] Add confidence threshold tuning based on SNR
- [ ] Log classification statistics (accuracy per mode)
- [ ] Add manual mode override in UI

### Medium-term
- [ ] Support multiple models (wideband, narrowband)
- [ ] Fine-tune on OpenWebRX-specific signals
- [ ] Add model versioning/updates

### Long-term
- [ ] Train custom model on real captured data
- [ ] Add time-series classification (mode changes)
- [ ] Integrate with automatic recording

---

## References

- **TorchSig 1.1.0:** https://github.com/TorchDSP/torchsig/releases/tag/v1.1.0
- **ONNX Runtime:** https://onnxruntime.ai/
- **Sig53 Paper:** https://arxiv.org/abs/2207.09918
- **EfficientNet Paper:** https://arxiv.org/abs/1905.11946

---

## Files Modified

- `Dockerfile.dev` - Replace PyTorch with ONNX Runtime
- `owrx/signal_classifier.py` - ONNX inference implementation
- `owrx/controllers/settings/decoding.py` - Settings page (already fixed)
- `export_torchsig_to_onnx.py` - Model export script (new)

---

## Migration Checklist

- [ ] Phase 1: Export model to ONNX
  - [ ] Install TorchSig 1.1.0
  - [ ] Run export script
  - [ ] Verify ONNX model works
  - [ ] Copy model file to project

- [ ] Phase 2: Update Docker
  - [ ] Update Dockerfile.dev
  - [ ] Add ONNX model to image
  - [ ] Test image builds
  - [ ] Verify image size reduction

- [ ] Phase 3: Update code
  - [ ] Rewrite signal_classifier.py
  - [ ] Update model loading
  - [ ] Update inference code
  - [ ] Test locally

- [ ] Phase 4: Testing
  - [ ] Test with FM signal
  - [ ] Test with digital modes
  - [ ] Verify confidence scores
  - [ ] Check CPU/memory usage

- [ ] Phase 5: Documentation
  - [ ] Update README
  - [ ] Update installation docs
  - [ ] Add ONNX guide
  - [ ] Update settings help

- [ ] Phase 6: Deployment
  - [ ] Commit changes
  - [ ] Create PR
  - [ ] Deploy to production
  - [ ] Monitor predictions

---

**Last Updated:** 2025-11-22
**Branch:** `claude/onnx-signal-classifier`
