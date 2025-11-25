# Step 2: Docker Integration

## Goal
Replace the 3.7 GB PyTorch stack with 20 MB ONNX Runtime in the Docker image.

## Why This Step?
- **Massive size reduction:** 3.7 GB → 20 MB (98% smaller!)
- **Faster builds:** No more 15-minute PyTorch downloads
- **Faster startup:** Container starts in seconds, not minutes
- **Lower memory:** Runtime uses ~100 MB instead of ~800 MB

## Prerequisites
- Completed Step 1 (have the `.onnx` file)
- Docker installed
- ~10 GB free space (for Docker build)

## Time Required
- First build: ~10-15 minutes (downloading base image + dependencies)
- Subsequent builds: ~2-3 minutes (with layer caching)

---

## File Changes

### 1. Copy ONNX Model to Project

```bash
# From the directory where you exported the model
cp torchsig_efficientnet_b0_sig53.onnx /home/michael/Projects/Radio/OpenWebRX/openwebrx+/
```

### 2. Update Dockerfile.dev

**File:** `openwebrx+/Dockerfile.dev`

**Before (TorchSig 2.0):**
```dockerfile
# Install PyTorch and major dependencies first (cacheable layer)
# This downloads ~3.7GB and takes 15-20 minutes
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    torch==2.9.1 \
    torchvision==0.24.1 \
    torchaudio==2.9.1 \
    numpy==1.26.4 \
    scipy==1.16.3 \
    matplotlib==3.10.7 \
    pandas==2.3.3 \
    scikit-learn==1.7.2

# Install torchsig from GitHub source (not available on PyPI)
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    https://github.com/TorchDSP/torchsig/archive/refs/heads/main.tar.gz
```

**After (ONNX Runtime):**
```dockerfile
# Install ONNX Runtime (much lighter than PyTorch!)
# PyTorch + TorchSig: ~3.7 GB, 15-20 min download
# ONNX Runtime: ~20 MB, <1 min download
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    onnxruntime==1.16.3 \
    numpy==1.23.5

# Copy pre-exported ONNX model (contains pretrained weights)
COPY torchsig_efficientnet_b0_sig53.onnx /usr/share/openwebrx/models/torchsig_efficientnet_b0_sig53.onnx
```

**Key Changes:**
- Removed: torch, torchvision, torchaudio, scipy, matplotlib, pandas, scikit-learn, torchsig
- Added: onnxruntime (1.16.3)
- Downgraded: numpy (1.26.4 → 1.23.5 for ONNX compatibility)
- New: COPY command to include ONNX model in image

---

## Full Updated Dockerfile.dev

Here's the complete updated file for reference:

```dockerfile
# Development Dockerfile for customized OpenWebRX+
# Uses ONNX Runtime for signal classification (lightweight!)

FROM slechev/openwebrxplus-softmbe:latest

# Install Python development tools
RUN apt update && apt install -y --no-install-recommends \
    python3-pip \
    python3-setuptools \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install ONNX Runtime for signal classification (much lighter than PyTorch!)
# Before: PyTorch + TorchSig = ~3.7 GB, 15-20 min download
# After:  ONNX Runtime = ~20 MB, <1 min download
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    onnxruntime==1.16.3 \
    numpy==1.23.5

# Create model directory
RUN mkdir -p /usr/share/openwebrx/models

# Copy pre-exported ONNX model with pretrained Sig53 weights
# This replaces the need for TorchSig + PyTorch at runtime
COPY torchsig_efficientnet_b0_sig53.onnx /usr/share/openwebrx/models/

# Copy your customized OpenWebRX+ code
WORKDIR /tmp/openwebrx-custom
COPY . .

# Install your customized version over the packaged one
# This preserves all the SDR libraries and dependencies
RUN python3 setup.py install --force

# Clean up
RUN rm -rf /tmp/openwebrx-custom

# Use the standard entrypoint from the base image
WORKDIR "/"
ENTRYPOINT ["/init"]
VOLUME /etc/openwebrx
VOLUME /var/lib/openwebrx

EXPOSE 8073
```

---

## Verification

### Check ONNX Model is Copied
After building, verify the model is in the image:

```bash
docker run --rm owrx-custom:dev ls -lh /usr/share/openwebrx/models/
```

Expected:
```
total 32M
-rw-r--r-- 1 root root 32M Nov 22 04:30 torchsig_efficientnet_b0_sig53.onnx
```

### Check ONNX Runtime is Installed
```bash
docker run --rm owrx-custom:dev python3 -c "import onnxruntime; print(f'ONNX Runtime {onnxruntime.__version__} installed')"
```

Expected:
```
ONNX Runtime 1.16.3 installed
```

### Check PyTorch is NOT Installed
```bash
docker run --rm owrx-custom:dev python3 -c "import torch" 2>&1 | grep -q "No module" && echo "✅ PyTorch not installed (good!)" || echo "❌ PyTorch still installed"
```

Expected:
```
✅ PyTorch not installed (good!)
```

---

## Build Instructions

### 1. Ensure ONNX File is Present
```bash
cd /home/michael/Projects/Radio/OpenWebRX/openwebrx+
ls -lh torchsig_efficientnet_b0_sig53.onnx
```

### 2. Build Docker Image
```bash
cd /home/michael/Projects/Radio/OpenWebRX
docker-compose -f docker-compose.dev.yml build --no-cache
```

**Why `--no-cache`?**
- Forces removal of old PyTorch layers
- Ensures numpy downgrade is applied
- Prevents layer conflicts

**Build time:** ~10-15 minutes (much faster than with PyTorch!)

### 3. Check Image Size
```bash
docker images | grep owrx-custom
```

**Before (with PyTorch):**
```
owrx-custom   dev   5.2 GB
```

**After (with ONNX):**
```
owrx-custom   dev   1.6 GB
```

**Savings:** 3.6 GB! 🎉

---

## Testing the Image

### Start Container
```bash
docker stop owrx-custom 2>/dev/null || true
docker rm owrx-custom 2>/dev/null || true
docker-compose -f docker-compose.dev.yml up -d
```

### Watch Logs
```bash
docker logs owrx-custom -f
```

**Look for:**
```
Loading TorchSig ONNX model from: /usr/share/openwebrx/models/torchsig_efficientnet_b0_sig53.onnx
ONNX model loaded successfully
  Input: iq_samples, shape: [1, 4096]
  Output: logits, shape: [1, 53]
```

**Should NOT see:**
```
Failed to load ONNX model: [Errno 2] No such file or directory
```

### Check Memory Usage
```bash
docker stats owrx-custom --no-stream
```

**Expected:**
- Memory usage: ~200-400 MB (with ONNX)
- Was: ~800-1200 MB (with PyTorch)

---

## Troubleshooting

### Issue: "No such file or directory: torchsig_efficientnet_b0_sig53.onnx"
**During build?**
- Check file exists in `openwebrx+/` directory
- Verify COPY command path is correct
- Try absolute path: `COPY /home/michael/.../model.onnx /usr/share/...`

**During runtime?**
- Model not copied to image
- Rebuild with `--no-cache`
- Check `docker run --rm owrx-custom:dev ls /usr/share/openwebrx/models/`

### Issue: "ImportError: No module named 'onnxruntime'"
**Cause:** ONNX Runtime not installed
**Solution:**
- Check pip install command ran successfully
- Look for errors in build logs: `docker-compose build 2>&1 | grep -i error`
- Try building without `--break-system-packages` flag

### Issue: "Incompatible numpy version"
**Cause:** numpy 1.26.4 is too new for onnxruntime 1.16.3
**Solution:**
- Downgrade numpy to 1.23.5 (as shown above)
- Or upgrade onnxruntime to 1.17+ (may need testing)

### Issue: Build fails with "network error"
**Cause:** PyPI/package server unreachable
**Solution:**
- Check internet connection
- Try again (transient network issues)
- Use different package index: `--index-url https://pypi.org/simple`

### Issue: Image is still huge (>4 GB)
**Cause:** Old layers not removed
**Solution:**
- Build with `--no-cache`
- Prune old images: `docker image prune -a`
- Check if PyTorch is still installed (see verification above)

---

## Size Comparison

| Component | Before (TorchSig 2.0) | After (ONNX) | Savings |
|-----------|----------------------|--------------|---------|
| Base image | 1.5 GB | 1.5 GB | 0 GB |
| PyTorch | 1.2 GB | - | 1.2 GB |
| TorchVision | 0.6 GB | - | 0.6 GB |
| TorchAudio | 0.4 GB | - | 0.4 GB |
| Dependencies | 1.5 GB | - | 1.5 GB |
| ONNX Runtime | - | 20 MB | - |
| ONNX Model | - | 50 MB | - |
| **Total** | **5.2 GB** | **1.6 GB** | **3.6 GB** |

---

## GPU Support (Optional)

If you want CUDA acceleration for faster inference:

### Update Dockerfile
```dockerfile
# Install ONNX Runtime with GPU support
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    onnxruntime-gpu==1.16.3 \
    numpy==1.23.5
```

### Update docker-compose
```yaml
services:
  owrx:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

**Note:** GPU version is ~150 MB (vs 20 MB CPU), but still **95% smaller** than PyTorch!

---

## Next Step

**→ [Step 3: Code Migration](STEP3_CODE_MIGRATION.md)**

Update `signal_classifier.py` to use ONNX Runtime instead of PyTorch.

---

## Key Points to Remember

✅ **Build once, deploy anywhere:** ONNX model is embedded in the image

✅ **Much faster builds:** No more waiting for PyTorch downloads

✅ **Smaller images:** 98% reduction in ML dependencies

✅ **Same functionality:** ONNX Runtime provides equivalent inference

✅ **Production ready:** ONNX is optimized for deployment

---

**Status:** Docker image ready, proceed to Step 3 ✅
