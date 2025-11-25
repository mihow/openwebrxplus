# Step 1: Export TorchSig Model to ONNX

## Goal
Create a portable ONNX model file from TorchSig 1.1.0's pretrained EfficientNet-B0.

## Why This Step?
- Separates training dependencies from production runtime
- Creates a single file with model architecture + pretrained weights
- Only needs to be done once (can reuse the `.onnx` file everywhere)

## Prerequisites
- Any machine with Python 3.7+ (can be your dev machine, doesn't need to be the server)
- ~2 GB free space (temporary, for PyTorch download)
- Internet connection (to download pretrained weights)

## Time Required
- First time: ~15-20 minutes (PyTorch download)
- Subsequent times: ~2-3 minutes (if PyTorch cached)

---

## Installation

### Create Virtual Environment (Recommended)
```bash
cd /home/michael/Projects/Radio/OpenWebRX
python3 -m venv torchsig-export-env
source torchsig-export-env/bin/activate
```

### Install Dependencies
```bash
# PyTorch 1.13.1 (compatible with TorchSig 1.1.0)
pip install torch==1.13.1 --index-url https://download.pytorch.org/whl/cpu

# ONNX tools
pip install onnx onnxruntime

# TorchSig 1.1.0 (has pretrained weights!)
pip install https://github.com/TorchDSP/torchsig/archive/refs/tags/v1.1.0.tar.gz
```

**Note:** Using CPU-only PyTorch to save bandwidth. GPU not needed for export.

---

## Export Process

### Run the Export Script
```bash
python3 export_torchsig_to_onnx.py
```

### What Happens
1. **Load TorchSig model:** Downloads pretrained EfficientNet-B0 weights (~30 MB)
2. **Create dummy input:** Generates test IQ samples (4096 complex samples)
3. **Test PyTorch inference:** Verifies model works before export
4. **Export to ONNX:** Converts model + weights to `.onnx` format
5. **Verify ONNX:** Checks exported model is valid
6. **Test ONNX Runtime:** Compares ONNX output with PyTorch output

### Expected Output
```
============================================================
TorchSig EfficientNet-B0 → ONNX Exporter
============================================================

Loading TorchSig EfficientNet-B0 with pretrained weights...
  Downloading pretrained weights...
  ✅ Model loaded successfully!
  Model type: <class 'torchsig.models.iq_models.efficientnet.EfficientNet'>

Creating dummy input (size=4096)...
  Input shape: torch.Size([1, 4096])
  Input dtype: torch.complex64

Testing PyTorch inference...
  Output shape: torch.Size([1, 53])
  Output classes: 53 (Sig53 modulation types)
  ✅ PyTorch inference successful!

Exporting to ONNX format...
  Output file: torchsig_efficientnet_b0_sig53.onnx
  ✅ Export successful!
  📦 File size: 32.4 MB

Verifying ONNX model...
  ✅ ONNX model is valid!

  Model Info:
    IR version: 9
    Producer: pytorch
    Opset version: 14

Testing with ONNX Runtime...
  ✅ ONNX Runtime inference successful!
  Output shape: (1, 53)

  Comparing ONNX vs PyTorch outputs:
    Max difference:  0.000012
    Mean difference: 0.000003
    ✅ Excellent match (diff < 1e-5)

============================================================
✅ Export Complete!
============================================================

Next steps:
  1. Copy torchsig_efficientnet_b0_sig53.onnx to your OpenWebRX directory:
     cp torchsig_efficientnet_b0_sig53.onnx openwebrx+/

  2. Update Dockerfile.dev to use onnxruntime instead of torch
     (See STEP2_DOCKER_INTEGRATION.md for details)

  3. Update owrx/signal_classifier.py to load ONNX model
     (See STEP3_CODE_MIGRATION.md for full code)

  4. Rebuild Docker image and enjoy:
     • 3.6 GB smaller image
     • Faster startup
     • Lower memory usage

============================================================
```

---

## Output File

**File:** `torchsig_efficientnet_b0_sig53.onnx`
**Size:** ~30-50 MB
**Contains:**
- Model architecture (EfficientNet-B0 adapted for 1D IQ signals)
- Pretrained weights (trained on Sig53 dataset)
- Input/output specifications
- Metadata

---

## Verification Steps

### 1. Check File Exists
```bash
ls -lh torchsig_efficientnet_b0_sig53.onnx
```
Expected: `-rw-r--r-- 1 michael michael 32M Nov 22 04:30 torchsig_efficientnet_b0_sig53.onnx`

### 2. Verify with ONNX Tools
```bash
python3 -c "import onnx; model = onnx.load('torchsig_efficientnet_b0_sig53.onnx'); print('Inputs:', [i.name for i in model.graph.input]); print('Outputs:', [o.name for o in model.graph.output])"
```
Expected:
```
Inputs: ['iq_samples']
Outputs: ['logits']
```

### 3. Test Inference
```python
import onnxruntime as ort
import numpy as np

# Load model
session = ort.InferenceSession('torchsig_efficientnet_b0_sig53.onnx')

# Create test input (4096 complex samples)
test_input = np.random.randn(1, 4096).astype(np.complex64)

# Run inference
outputs = session.run(None, {'iq_samples': test_input})

# Check output
print(f"Output shape: {outputs[0].shape}")  # Should be (1, 53)
print(f"Output range: [{outputs[0].min():.2f}, {outputs[0].max():.2f}]")
print(f"✅ Model works!")
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'torchsig'"
**Solution:** TorchSig not installed. Run:
```bash
pip install https://github.com/TorchDSP/torchsig/archive/refs/tags/v1.1.0.tar.gz
```

### Issue: "Could not download pretrained weights"
**Solution:** Network issue. Check internet connection or try:
```python
# In the export script, add path parameter
model = efficientnet_b0(pretrained=True, path="/path/to/downloaded/weights.pth")
```

### Issue: "RuntimeError: ONNX export failed"
**Possible causes:**
- PyTorch version incompatible (use 1.13.1)
- Model has unsupported operations
- Try different opset version: `opset_version=11` or `opset_version=13`

### Issue: "Large difference between PyTorch and ONNX outputs"
**Investigation:**
- Check if difference is consistent (same for all inputs)
- If difference < 1e-3, it's acceptable for inference
- If difference > 1e-2, may indicate export issue

---

## Cleanup (Optional)

After successful export, you can remove the temporary environment:

```bash
deactivate
rm -rf torchsig-export-env
```

**Keep the ONNX file!** You'll need it for the next step.

---

## Next Step

**→ [Step 2: Docker Integration](STEP2_DOCKER_INTEGRATION.md)**

Copy the ONNX file to your project and update the Dockerfile.

---

## Key Points to Remember

✅ **Export is one-time:** Once you have the `.onnx` file, you never need PyTorch again

✅ **File is portable:** Can use the same `.onnx` file on any platform (Linux, Windows, macOS, ARM, x86)

✅ **Weights are embedded:** The `.onnx` file contains both architecture and pretrained weights

✅ **Version specific:** This export is for TorchSig 1.1.0's EfficientNet-B0. Different versions may need re-export.

✅ **Size is fixed:** The ~30-50 MB file size is permanent (contains all weights)

---

**Status:** Ready for Step 2 ✅
