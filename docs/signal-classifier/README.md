# Signal Classification Plugin for OpenWebRX+

Automatic signal classification and modulation prediction using TorchSig, a PyTorch-based deep learning toolkit for wireless signal processing.

## Features

- Real-time signal classification using machine learning
- Predicts modulation type (AM, FM, SSB, CW, digital modes, etc.)
- Displays confidence scores for predictions
- Maps TorchSig classifications to OpenWebRX+ mode names
- Configurable confidence threshold and update interval
- Optional GPU acceleration with CUDA

## Requirements

- Python 3.8+
- PyTorch
- TorchSig
- NumPy

## Installation

```bash
pip install torch torchsig numpy
```

For GPU acceleration (optional):
```bash
pip install torch torchsig numpy --index-url https://download.pytorch.org/whl/cu118
```

## Configuration

Access signal classifier settings via the web interface:

**Settings > Demodulation and decoding > Signal classifier**

Available options:

| Setting | Default | Description |
|---------|---------|-------------|
| `signal_classifier_enabled` | `false` | Enable/disable signal classification |
| `signal_classifier_threshold` | `0.5` | Minimum confidence threshold (0.0-1.0) |
| `signal_classifier_interval` | `1.0` | Classification interval in seconds |
| `signal_classifier_device` | `cpu` | Inference device (`cpu` or `cuda`) |

## How It Works

1. The classifier receives IQ samples from the current receiver passband
2. Samples are accumulated until the configured interval is reached
3. TorchSig's EfficientNet-B0 model analyzes the signal
4. Top predictions are filtered by confidence threshold
5. Results are sent to the UI via WebSocket

## Supported Modulation Types

TorchSig's Sig53 dataset includes 53 modulation classes. The plugin maps these to OpenWebRX+ modes:

| TorchSig Class | OpenWebRX+ Mode |
|----------------|-----------------|
| am-dsb | AM |
| am-lsb | LSB |
| am-usb | USB |
| fm | NFM |
| ook | CW |
| bpsk | BPSK31 |
| 4fsk/4gfsk | DMR |
| gmsk | D-Star |
| ofdm-64 | FT8 |
| ofdm-2048 | DAB |

## Architecture

```
                    ┌─────────────────┐
IQ Samples ──────┬──│   Demodulator   │──► Audio
  (from SDR)     │  └─────────────────┘
                 │
                 │  ┌─────────────────┐     ┌──────────────┐
                 └──│ SignalClassifier│─────│   WebSocket  │──► UI Panel
                    └─────────────────┘     └──────────────┘
```

The classifier runs in parallel with the main demodulation chain, processing the same IQ data without affecting audio output.

## Performance Considerations

- Classification runs asynchronously to avoid blocking audio
- Model loading is lazy and cached (loaded on first use)
- GPU acceleration significantly improves inference speed
- Increase interval for lower CPU usage

## Limitations

- TorchSig models are trained on synthetic data; real-world accuracy may vary
- Some OpenWebRX+ modes don't have direct TorchSig equivalents
- Classification accuracy depends on signal quality and bandwidth

## Troubleshooting

### TorchSig not detected
- Ensure `torchsig` and `torch` are installed
- Restart OpenWebRX+ after installation
- Check feature report: `python3 -m owrx.feature`

### Low classification accuracy
- Increase the confidence threshold
- Ensure adequate signal strength
- Try different sample rates

### High CPU usage
- Increase the classification interval
- Use GPU acceleration if available

## References

- [TorchSig GitHub](https://github.com/TorchDSP/torchsig)
- [TorchSig Documentation](https://torchsig.readthedocs.io/)
- [Sig53 Dataset Paper](https://arxiv.org/abs/2110.06599)
