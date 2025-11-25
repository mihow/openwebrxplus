# TorchSig Signal Classifier Installation Guide

This document provides instructions for installing TorchSig to enable automatic signal classification in OpenWebRX+.

## What is TorchSig?

TorchSig is a PyTorch-based deep learning toolkit for wireless signal processing developed by the TorchDSP team. It provides pre-trained models for signal classification that can identify 50+ modulation types including AM, FM, SSB, PSK, FSK, QAM, and OFDM variants.

- **Repository**: https://github.com/TorchDSP/torchsig
- **Documentation**: https://torchsig.readthedocs.io/
- **License**: MIT

## Requirements

- Python 3.10 or higher (TorchSig v2.0 requirement)
- Ubuntu 22.04+ (recommended)
- 4GB+ RAM (16GB+ recommended for GPU)
- ~2GB disk space for model weights

## Installation Methods

**Note:** TorchSig is not available on PyPI and must be installed from GitHub.

### Method 1: Clone and Install (Recommended by TorchSig)

```bash
# Clone repository and install in development mode
git clone https://github.com/TorchDSP/torchsig.git
cd torchsig
pip install torch numpy
pip install -e .

# Verify installation
python3 -c "import torch; import torchsig; print('TorchSig installed successfully')"
```

### Method 2: Direct pip install from GitHub

```bash
# CPU-only installation (simpler but no updates)
pip install torch numpy
pip install git+https://github.com/TorchDSP/torchsig.git

# Verify installation
python3 -c "import torch; import torchsig; print('TorchSig installed successfully')"
```

### Method 3: Install with CUDA (GPU acceleration)

For NVIDIA GPU users:

```bash
# Install PyTorch with CUDA support (adjust cuda version as needed)
pip install torch --index-url https://download.pytorch.org/whl/cu118

# Install TorchSig from GitHub
pip install numpy
pip install git+https://github.com/TorchDSP/torchsig.git

# Verify CUDA availability
python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### Method 4: Install in Virtual Environment

```bash
# Create virtual environment
python3 -m venv ~/openwebrx-venv
source ~/openwebrx-venv/bin/activate

# Install packages
pip install torch numpy
pip install git+https://github.com/TorchDSP/torchsig.git

# Deactivate when done
deactivate
```

Note: If using a virtual environment, ensure OpenWebRX+ runs with the same Python environment.

### Method 5: System-wide Installation (Debian/Ubuntu)

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-numpy git

# Install PyTorch and TorchSig
sudo pip3 install torch
sudo pip3 install git+https://github.com/TorchDSP/torchsig.git
```

## Verification

### Check Feature Detection

```bash
# Run OpenWebRX+ feature detection
python3 -m owrx.feature | grep -A5 signal_classifier
```

Expected output:
```
signal_classifier:
  available: true
  requirements:
    torchsig:
      available: true
      enabled: true
```

### Check in Web Interface

1. Open OpenWebRX+ admin panel
2. Navigate to **Settings > Features**
3. Look for "signal_classifier" - should show green checkmark

### Test Import

```bash
python3 -c "
from owrx.signal_classifier import is_available, get_config
print('Available:', is_available())
print('Config:', get_config())
"
```

## Configuration

After installation, enable the classifier in the web interface:

1. Go to **Settings > Demodulation and decoding**
2. Scroll to **Signal classifier** section
3. Check **Enable automatic signal classification**
4. Adjust settings as needed:
   - **Confidence threshold**: 0.5 (default) - minimum confidence to display
   - **Classification interval**: 1.0s (default) - how often to classify
   - **Inference device**: CPU or CUDA

## Model Download

The first time the classifier runs, it will download the pre-trained EfficientNet-B0 model (~50MB). This happens automatically but requires internet access.

To pre-download the model:

```bash
python3 -c "
from torchsig.models import efficientnet_b0
model = efficientnet_b0(pretrained=True, num_classes=53)
print('Model downloaded successfully')
"
```

## Troubleshooting

### "No module named torchsig"

TorchSig must be installed from GitHub (not available on PyPI):
```bash
pip install git+https://github.com/TorchDSP/torchsig.git
```

### "No module named torch"

PyTorch is not installed:
```bash
pip install torch
```

### Feature shows unavailable after installation

Clear the feature cache and restart:
```bash
# Restart OpenWebRX+
sudo systemctl restart openwebrx
```

### CUDA out of memory

Switch to CPU inference in settings, or reduce classification interval.

### Slow classification

- Increase classification interval (e.g., 2.0s)
- Use GPU acceleration if available
- Model loads lazily on first use - first classification may be slow

### Wrong Python version

Ensure TorchSig is installed for the same Python version OpenWebRX+ uses:
```bash
# Check which Python OpenWebRX+ uses
which python3

# Install for that specific Python
/usr/bin/python3 -m pip install torch numpy
/usr/bin/python3 -m pip install git+https://github.com/TorchDSP/torchsig.git
```

## Docker Installation (Advanced)

TorchSig provides official Docker images with CUDA support. This can be useful for:
- Development/testing environments
- GPU-accelerated deployments
- Avoiding dependency conflicts

### Using TorchSig Docker Image

```bash
# Pull or build TorchSig image
git clone https://github.com/TorchDSP/torchsig.git
cd torchsig
docker build -t torchsig:latest .

# Run with GPU support
docker run --gpus all -it torchsig:latest
```

### Integration with OpenWebRX+ Docker

For Docker-based OpenWebRX+ deployments, you can extend the TorchSig base image or copy the installed packages. The TorchSig Dockerfile uses:
- Base: `nvidia/cuda:12.1.0-runtime-ubuntu22.04`
- Python 3.10
- Pre-compiled Rust extensions for performance

See the [TorchSig Dockerfile](https://github.com/TorchDSP/torchsig/blob/main/Dockerfile) for implementation details.

## Uninstallation

```bash
pip uninstall torchsig torch
```

To disable without uninstalling, simply uncheck "Enable automatic signal classification" in settings.

## Hardware Requirements by Configuration

| Configuration | RAM | CPU | Notes |
|--------------|-----|-----|-------|
| CPU (default) | 4GB+ | Any modern | ~1s per classification |
| CUDA GPU | 4GB+ | + NVIDIA GPU | ~50ms per classification |

## Next Steps

After installation, see [TESTING.md](TESTING.md) to verify the classifier is working correctly.
