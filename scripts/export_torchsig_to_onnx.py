#!/usr/bin/env python3
"""
Export TorchSig 1.1.0 EfficientNet-B0 pretrained model to ONNX format.
Run this once to generate the ONNX file, then you can use ONNX Runtime.

Usage:
    python3 export_torchsig_to_onnx.py

Requirements:
    pip install torch==1.13.1 onnx onnxruntime
    pip install https://github.com/TorchDSP/torchsig/archive/refs/tags/v1.1.0.tar.gz
"""

import torch
import numpy as np
import sys
import os

def export_to_onnx():
    print("="*60)
    print("TorchSig EfficientNet-B0 → ONNX Exporter")
    print("="*60)
    print()

    print("Loading TorchSig EfficientNet-B0 with pretrained weights...")

    try:
        from torchsig.models.iq_models import efficientnet_b0
    except ImportError:
        print()
        print("❌ ERROR: TorchSig 1.1.0 not installed!")
        print()
        print("Install with:")
        print("  pip install torch==1.13.1")
        print("  pip install https://github.com/TorchDSP/torchsig/archive/refs/tags/v1.1.0.tar.gz")
        sys.exit(1)

    # Load pretrained model
    print("  Downloading pretrained weights...")
    model = efficientnet_b0(pretrained=True, path=None)
    model.eval()

    print(f"  ✅ Model loaded successfully!")
    print(f"  Model type: {type(model)}")
    print()

    # Determine expected input size
    # TorchSig models typically expect specific buffer sizes
    # Common sizes: 1024, 2048, 4096, 8192
    input_size = 4096

    print(f"Creating dummy input (size={input_size})...")
    # Create dummy input (batch_size=1, IQ samples as complex64)
    dummy_iq = torch.randn(1, input_size, dtype=torch.complex64)

    print(f"  Input shape: {dummy_iq.shape}")
    print(f"  Input dtype: {dummy_iq.dtype}")
    print()

    # Test inference before export
    print("Testing PyTorch inference...")
    with torch.no_grad():
        output = model(dummy_iq)
        print(f"  Output shape: {output.shape}")
        print(f"  Output classes: {output.shape[-1]} (Sig53 modulation types)")
        print(f"  ✅ PyTorch inference successful!")
    print()

    # Export to ONNX
    output_path = "torchsig_efficientnet_b0_sig53.onnx"
    print(f"Exporting to ONNX format...")
    print(f"  Output file: {output_path}")

    torch.onnx.export(
        model,
        dummy_iq,
        output_path,
        export_params=True,          # Store trained parameters
        opset_version=14,            # ONNX opset version (14 is widely supported)
        do_constant_folding=True,    # Optimize constant folding
        input_names=['iq_samples'],  # Input tensor name
        output_names=['logits'],     # Output tensor name
        dynamic_axes={
            'iq_samples': {0: 'batch_size'},  # Variable batch size
            'logits': {0: 'batch_size'}
        },
        verbose=False
    )

    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    print(f"  ✅ Export successful!")
    print(f"  📦 File size: {file_size:.1f} MB")
    print()

    # Verify the exported model
    print("Verifying ONNX model...")
    try:
        import onnx
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        print("  ✅ ONNX model is valid!")

        # Print model info
        print()
        print("  Model Info:")
        print(f"    IR version: {onnx_model.ir_version}")
        print(f"    Producer: {onnx_model.producer_name}")
        print(f"    Opset version: {onnx_model.opset_import[0].version}")
        print()

    except ImportError:
        print("  ⚠️  'onnx' package not installed, skipping verification")
        print("     Install with: pip install onnx")
        print()

    # Test with ONNX Runtime
    print("Testing with ONNX Runtime...")
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(output_path)

        # Convert dummy input to numpy
        dummy_np = dummy_iq.numpy()

        # Run inference
        outputs = session.run(None, {'iq_samples': dummy_np})
        print(f"  ✅ ONNX Runtime inference successful!")
        print(f"  Output shape: {outputs[0].shape}")

        # Compare with PyTorch output
        torch_output = output.numpy()
        onnx_output = outputs[0]

        max_diff = np.abs(torch_output - onnx_output).max()
        mean_diff = np.abs(torch_output - onnx_output).mean()

        print()
        print("  Comparing ONNX vs PyTorch outputs:")
        print(f"    Max difference:  {max_diff:.6f}")
        print(f"    Mean difference: {mean_diff:.6f}")

        if max_diff < 1e-5:
            print(f"    ✅ Excellent match (diff < 1e-5)")
        elif max_diff < 1e-3:
            print(f"    ✅ Good match (diff < 1e-3, acceptable for inference)")
        elif max_diff < 1e-2:
            print(f"    ⚠️  Acceptable match (diff < 1e-2, minor differences)")
        else:
            print(f"    ❌ Large difference! May need investigation")

    except ImportError:
        print("  ⚠️  'onnxruntime' package not installed, skipping runtime test")
        print("     Install with: pip install onnxruntime")

    print()
    print("="*60)
    print("✅ Export Complete!")
    print("="*60)
    print()
    print("Next steps:")
    print(f"  1. Copy {output_path} to your OpenWebRX directory:")
    print(f"     cp {output_path} openwebrx+/")
    print()
    print(f"  2. Update Dockerfile.dev to use onnxruntime instead of torch")
    print(f"     (See ONNX_EXPORT_GUIDE.md for details)")
    print()
    print(f"  3. Update owrx/signal_classifier.py to load ONNX model")
    print(f"     (See ONNX_EXPORT_GUIDE.md for full code)")
    print()
    print(f"  4. Rebuild Docker image and enjoy:")
    print(f"     • 3.6 GB smaller image")
    print(f"     • Faster startup")
    print(f"     • Lower memory usage")
    print()
    print("="*60)

if __name__ == "__main__":
    try:
        export_to_onnx()
    except KeyboardInterrupt:
        print("\n\n⚠️  Export cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
