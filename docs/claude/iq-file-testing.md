# IQ File Playback Testing Design

## Overview

This document describes the design for automated testing of OpenWebRX+ using pre-recorded IQ files, eliminating the need for physical SDR hardware during testing and enabling a demo mode for users.

## Goals

1. **Automated CI/CD Testing** - Run decoder tests without hardware
2. **Demo Mode** - Users can explore the UI with real signals without an SDR
3. **Regression Testing** - Reproducible tests with known inputs/outputs
4. **Developer Experience** - Faster iteration without hardware setup

## Architecture

### FileSource Class

A new SDR source type that reads IQ files instead of hardware input.

```
IQ File → Playback Process → nmux → TcpSource → DSP Chain → Decoders
```

#### Class Hierarchy

```
SdrSource
└── DirectSource
    └── FileSource  (new)
```

#### Key Features

- Reads `.cf32` (complex float32) IQ files
- Configurable sample rate and center frequency
- Loop mode for continuous playback
- Rate-limited playback to simulate real-time
- Metadata via JSON sidecar files

### File Format

**Primary format:** Complex Float 32-bit (`.cf32`)
- Native to pycsdr/csdr toolchain
- 8 bytes per sample (4 bytes I + 4 bytes Q)
- Interleaved I/Q samples

**Metadata sidecar:** `<filename>.json`
```json
{
  "sample_rate": 48000,
  "center_frequency": 14074000,
  "description": "FT8 signals on 20m band",
  "duration_seconds": 60,
  "expected_decodes": ["CQ DX1ABC PM95", "DE W1AW"]
}
```

### Test Data Repository

```
test_data/iq/
├── ft8_14074khz_48k.cf32
├── ft8_14074khz_48k.json
├── fm_broadcast_98100khz_240k.cf32
├── fm_broadcast_98100khz_240k.json
├── aprs_144390khz_48k.cf32
├── aprs_144390khz_48k.json
└── README.md
```

## Implementation

### FileSource Class (`owrx/source/file.py`)

```python
class FileSource(DirectSource):
    """SDR source that plays back IQ files"""

    def getCommand(self):
        # Use pv for rate-limited playback, cat for looping
        file_path = self.props["file_path"]
        sample_rate = self.props["samp_rate"]
        byte_rate = sample_rate * 8  # cf32 = 8 bytes/sample

        if self.props.get("loop", True):
            cmd = f"while true; do cat {file_path}; done"
        else:
            cmd = f"cat {file_path}"

        # Rate limit with pv
        return [f"{cmd} | pv -qL {byte_rate}"] + self.getNmuxCommand()
```

### Configuration

```yaml
sdrs:
  demo_sdr:
    type: file
    name: "Demo SDR (FT8 Recording)"
    file_path: "/path/to/ft8_14074khz_48k.cf32"
    profiles:
      ft8:
        name: "20m FT8"
        center_freq: 14074000
        samp_rate: 48000
        start_freq: 14074000
        start_mod: usb
```

### Test Framework Integration

```python
# test/test_decoders.py
class TestFT8Decoder(unittest.TestCase):
    def setUp(self):
        self.source = FileSource("test", {
            "file_path": "test_data/iq/ft8_14074khz_48k.cf32",
            "samp_rate": 48000,
            "center_freq": 14074000,
            "loop": False
        })

    def test_ft8_decode(self):
        # Start source, collect decoder output, verify expected decodes
        pass
```

## Playback Methods

### Option 1: pv (Pipe Viewer) - Recommended

```bash
cat file.cf32 | pv -qL $BYTE_RATE | nmux ...
```
- Simple, widely available
- Accurate rate limiting
- Loop with: `while true; do cat file.cf32; done | pv -qL $RATE`

### Option 2: Custom Python Playback

For more control (seeking, pause, speed adjustment):
```python
# Could add htdocs controls for playback position
```

### Option 3: SoapySDR File Device

Some SoapySDR builds support file sources, but not universally available.

## Recording IQ Files

### Using rtl_sdr
```bash
rtl_sdr -f 14074000 -s 48000 -g 40 ft8_recording.cu8
# Convert to cf32
csdr convert_u8_f < ft8_recording.cu8 > ft8_recording.cf32
```

### Using hackrf_transfer
```bash
hackrf_transfer -r recording.cs8 -f 14074000 -s 2000000
```

### Using SoapySDR
```bash
SoapySDRUtil --probe  # find device
# Use rx_sdr or custom script
```

## Use Cases

### 1. CI/CD Pipeline

```yaml
# .github/workflows/test.yml
test:
  steps:
    - run: python -m pytest test/test_decoders.py
```

Tests run headless, validate decoder output matches expected.

### 2. Demo Mode

User configures a FileSource in settings, sees waterfall with real signals. Good for:
- Evaluating OpenWebRX+ before buying hardware
- Training/education
- Screenshots/documentation

### 3. Decoder Development

Developers can test decoder changes against known-good recordings without hardware.

## Phase 1 Implementation

1. `FileSource` class with basic playback
2. Sample FT8 recording (easy to obtain)
3. Basic pytest integration
4. Documentation

## Phase 2 Enhancements

1. Web UI playback controls (pause, seek, speed)
2. Multiple file sources for band scanning simulation
3. Signal injection (mix recorded signals with noise)
4. Automated recording capture tool

## Dependencies

- `pv` (pipe viewer) - standard on most Linux systems
- Existing csdr/pycsdr toolchain
- Test IQ files (to be recorded or sourced)

## Open Questions

1. Should we include sample IQ files in the repo (size concerns)?
2. License considerations for recorded broadcast content?
3. Integration with existing test framework vs. new test suite?
