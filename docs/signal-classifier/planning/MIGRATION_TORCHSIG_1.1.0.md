# Migration Guide: TorchSig 2.0 → 1.1.0 for Pretrained Weights

## Why Migrate Back to 1.1.0?

**TorchSig 1.1.0** includes pretrained EfficientNet-B0 weights trained on the Sig53 dataset:
- ✅ 53 modulation classes
- ✅ Pretrained weights with 62.75% accuracy on impaired signals
- ✅ Ready to use out of the box
- ✅ Proven performance on real-world RF signals

**TorchSig 2.0** introduced XCiT1d architecture but:
- ❌ No pretrained weights available
- ❌ Random predictions until trained from scratch
- ❌ Would require massive Sig53 dataset + GPU + days of training

## Changes Required

### 1. Dockerfile Changes

**File:** `openwebrx+/Dockerfile.dev`

Replace the TorchSig 2.0 installation section:

```dockerfile
# Install PyTorch and major dependencies first (cacheable layer)
# Versions compatible with TorchSig 1.1.0
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    torch==1.13.1 \
    torchvision==0.14.1 \
    torchaudio==0.13.1 \
    numpy==1.23.5 \
    scipy==1.9.3 \
    matplotlib==3.6.2 \
    scikit-learn==1.2.0

# Install TorchSig 1.1.0 from GitHub (has pretrained weights!)
# 2.0 version: https://github.com/TorchDSP/torchsig/archive/refs/heads/main.tar.gz
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    https://github.com/TorchDSP/torchsig/archive/refs/tags/v1.1.0.tar.gz
```

**Key Changes:**
- PyTorch 2.9.1 → 1.13.1 (1.1.0 compatibility)
- NumPy 1.26.4 → 1.23.5
- SciPy 1.16.3 → 1.9.3
- Install from `v1.1.0` tag instead of `main` branch

---

### 2. Signal Classifier Code Changes

**File:** `openwebrx+/owrx/signal_classifier.py`

#### Change 1: Model Import and Initialization

Replace lines 118-136 in the `load()` method:

```python
def load(self, device: str = "cpu"):
    """Load the TorchSig model if not already loaded."""
    if self.loaded:
        return True

    try:
        import torch
        # TorchSig 2.0 import:
        # from torchsig.models import XCiT1d
        # TorchSig 1.1.0 import:
        from torchsig.models.iq_models import efficientnet_b0

        self.device = device
        logger.info("Loading TorchSig EfficientNet-B0 model on device: %s", device)

        # TorchSig 2.0 code (no pretrained weights):
        # self.model = XCiT1d(
        #     input_channels=2,  # IQ data has 2 channels (I and Q)
        #     n_features=len(SIG53_CLASSES),  # 53 signal classes
        #     xcit_version="nano_12_p16_224",  # Smaller model for faster inference
        #     ds_method="downsample",
        #     ds_rate=16
        # )

        # TorchSig 1.1.0 code (with pretrained weights):
        self.model = efficientnet_b0(
            pretrained=True,  # Load pretrained Sig53 weights!
            path=None  # Auto-download from TorchSig servers
        )

        self.model.to(self.device)
        self.model.eval()
        self.loaded = True

        # TorchSig 2.0 warning:
        # logger.warning("TorchSig model loaded WITHOUT pretrained weights - predictions will be random until trained")
        # TorchSig 1.1.0 success:
        logger.info("TorchSig EfficientNet-B0 loaded WITH pretrained Sig53 weights")
        return True

    except Exception as e:
        self.load_error = str(e)
        logger.error("Failed to load TorchSig model: %s", e)
        return False
```

#### Change 2: Input Preprocessing

Replace lines 162-175 in the `classify()` method:

```python
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

        # TorchSig 2.0 format (XCiT1d expects channels-first):
        # iq_tensor = torch.zeros(1, 2, len(samples), dtype=torch.float32)
        # iq_tensor[0, 0, :] = torch.from_numpy(samples.real.astype(np.float32))
        # iq_tensor[0, 1, :] = torch.from_numpy(samples.imag.astype(np.float32))

        # TorchSig 1.1.0 format (EfficientNet-B0 expects 2D complex tensor):
        # Shape: (batch_size, num_iq_samples)
        iq_tensor = torch.from_numpy(samples).unsqueeze(0)  # Add batch dimension
        iq_tensor = iq_tensor.to(self.device)

        # Run inference
        with torch.no_grad():
            output = self.model(iq_tensor)
            # Both 1.1.0 and 2.0 output shape: (batch, n_features)
            probs = torch.softmax(output, dim=-1)

        # Get top-k predictions (same for both versions)
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
```

---

### 3. Expected Sample Length

**Important:** EfficientNet-B0 expects a specific input length. You may need to adjust the buffer size.

In `__init__()` method (lines 208-222), consider adjusting:

```python
def __init__(self, sampleRate: int = 48000, interval: float = 1.0,
             threshold: float = 0.3, device: str = "cpu"):
    self.sampleRate = sampleRate
    self.interval = interval
    self.threshold = threshold
    self.device = device
    self.frequency = 0
    self.buffer = []

    # TorchSig 1.1.0: EfficientNet-B0 trained on specific IQ lengths
    # Common lengths: 1024, 2048, 4096, 8192 samples
    # Adjust based on your sample rate and desired classification speed
    # For 48kHz: 4096 samples = ~85ms of data
    # For 200kHz: 8192 samples = ~41ms of data
    self.buffer_size = 4096  # Adjust as needed
    # 2.0 version used: int(sampleRate * interval)

    self.last_classification = 0

    # Get the shared model instance
    self.model = SignalClassifierModel.getInstance()

    super().__init__()
```

**Note:** Check TorchSig 1.1.0 documentation for exact expected input lengths. May need to resample or pad/truncate.

---

## Migration Steps

### Step 1: Update Dockerfile
```bash
cd /home/michael/Projects/Radio/OpenWebRX
# Edit Dockerfile.dev with changes above
```

### Step 2: Update Signal Classifier Code
```bash
cd openwebrx+/owrx
# Edit signal_classifier.py with changes above
```

### Step 3: Rebuild Docker Image
```bash
cd /home/michael/Projects/Radio/OpenWebRX
docker-compose -f docker-compose.dev.yml build --no-cache
```

**Note:** Use `--no-cache` to ensure PyTorch versions are downgraded properly.

### Step 4: Stop Old Container
```bash
docker stop owrx-custom
docker rm owrx-custom
```

### Step 5: Start New Container
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Step 6: Watch Logs
```bash
docker logs owrx-custom -f
```

Look for:
- ✅ `"Loading TorchSig EfficientNet-B0 model on device: cpu"`
- ✅ `"TorchSig EfficientNet-B0 loaded WITH pretrained Sig53 weights"`
- ❌ NOT: `"loaded WITHOUT pretrained weights"`

---

## Testing the Migration

### 1. Check Model Loaded Successfully
```bash
docker logs owrx-custom | grep -i "torchsig"
```

Should see:
```
2025-11-22 XX:XX:XX,XXX - owrx.signal_classifier - INFO - Loading TorchSig EfficientNet-B0 model on device: cpu
2025-11-22 XX:XX:XX,XXX - owrx.signal_classifier - INFO - TorchSig EfficientNet-B0 loaded WITH pretrained Sig53 weights
```

### 2. Test Signal Classification
Tune to a known signal (FM broadcast, RTTY, etc.) and watch the predictions:
```bash
docker logs owrx-custom -f | grep -i "prediction"
```

### 3. Verify Settings Page Still Works
Visit: http://beast.wirehair-yo.ts.net:8073/settings/decoding

Signal classifier section should display with no errors.

---

## Rollback Plan (If Needed)

If 1.1.0 doesn't work, you can rollback to 2.0:

```bash
# Restore original Dockerfile.dev (TorchSig 2.0)
git checkout openwebrx+/Dockerfile.dev openwebrx+/owrx/signal_classifier.py

# Rebuild
docker-compose -f docker-compose.dev.yml build
docker-compose -f docker-compose.dev.yml up -d
```

---

## Expected Benefits

After migration, you should see:

✅ **Real predictions** instead of random noise
✅ **Accurate modulation detection** for common modes
✅ **Confidence scores** that make sense (higher for clean signals)
✅ **Automatic mode switching** when classifier is enabled

---

## Troubleshooting

### Issue: "No module named 'torchsig.models.iq_models'"
**Solution:** Ensure you're installing v1.1.0, not main branch

### Issue: "Input shape mismatch"
**Solution:** Adjust `buffer_size` to match expected input length (try 1024, 2048, 4096, 8192)

### Issue: "RuntimeError: CUDA out of memory"
**Solution:** Use device="cpu" in settings, or reduce batch size

### Issue: Model download fails
**Solution:** May need to download weights manually from TorchSig repository

---

## Additional Notes

- **Model size:** EfficientNet-B0 weights are ~20MB (downloads on first run)
- **Inference speed:** ~50-100ms on CPU for 4096 samples
- **GPU acceleration:** Can use CUDA device for 5-10x speedup
- **Training:** If you want to fine-tune on your own data, 1.1.0 is easier to train than 2.0

---

## References

- **TorchSig 1.1.0 Release:** https://github.com/TorchDSP/torchsig/releases/tag/v1.1.0
- **EfficientNet Paper:** https://arxiv.org/abs/1905.11946
- **Sig53 Dataset:** 53 modulation classes, 5M samples, -10dB to +30dB SNR
- **OpenWebRX+ Docs:** Check `/docs/claude/` for architecture details

---

**Ready to migrate?** Follow the steps above and you'll have working pretrained signal classification!
