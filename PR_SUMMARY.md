# Add FileSource for Automated Testing and Demo Mode

## Summary

This PR enables automated testing and demo mode for OpenWebRX+ by implementing IQ file playback as a virtual SDR source. Users can now test the platform without physical SDR hardware and without waiting for real signals.

## Problem

OpenWebRX+ requires SDR hardware to test functionality, which creates several challenges:
- **No automated testing** - CI/CD pipelines can't run without hardware
- **Manual testing is slow** - Must wait for real signals (FT8, FM broadcasts, etc.)
- **Demo mode unavailable** - Users can't evaluate the platform before buying SDR hardware
- **Decoder regression testing impossible** - No reproducible test signals

## Solution

Implemented **FileSource** - a new SDR source type that plays back recorded IQ files:
- Integrates seamlessly with existing SDR source architecture
- Uses `pv` for rate-limited playback to simulate real-time data
- Supports looping for continuous demo mode
- Works with standard `.cf32` (complex float32) format

## What's Included

### 1. FileSource Implementation (`owrx/source/file.py`)
- New SDR source that reads IQ files instead of hardware
- Configurable sample rate and center frequency
- Loop mode for continuous playback
- Full integration with OpenWebRX+ settings UI

### 2. Test Signal Generator (`test/generate_test_iq.py`)
Generate synthetic IQ files without SDR hardware:
- **Signals:** Tone, AM, FM, Noise, Tone+Noise
- **Any sample rate:** 48kHz to 2.4MHz+
- **Configurable FM deviation** (default 75kHz for broadcast)
- **Auto-generated metadata** (JSON sidecar files)

Example:
```bash
# FM broadcast signal (240kHz sample rate)
python test/generate_test_iq.py --signal fm --frequency 100000 \
    --sample-rate 240000 --duration 1 --deviation 75000 \
    --center-freq 98100000 -o test_data/iq/fm_test.cf32
```

### 3. Sample Test Files
- `test_tone_1khz.cf32` - 48kHz, 2s tone for basic testing
- `test_fm_240k.cf32` - 240kHz FM signal with 75kHz deviation

### 4. CI/CD Workflow (`.github/workflows/test.yml`)
- **Unit tests** on Python 3.9, 3.10, 3.11
- **Integration tests** in Docker with pycsdr
- **Code quality** checks (flake8, black)
- All tests passing ✅

### 5. Comprehensive Documentation
- Design document (`docs/claude/iq-file-testing.md`)
- Usage guide (`test_data/iq/README.md`)
- Integration test suite

## Usage

### Demo Mode (No SDR Required)

Configure FileSource in settings:

```yaml
sdrs:
  demo:
    type: file
    name: "Demo FM Station"
    file_path: "/path/to/test_data/iq/test_fm_240k.cf32"
    loop: true
    profiles:
      fm:
        name: "FM Broadcast"
        center_freq: 98100000
        samp_rate: 240000
        start_freq: 98100000
        start_mod: wfm
```

Users can now:
- See waterfall with real signals
- Test all demodulators (AM, FM, SSB, etc.)
- Evaluate OpenWebRX+ before buying hardware

### Automated Testing

```python
# test/test_integration_file_source.py
def test_iq_file_playback(self):
    """Verify IQ file can be read and processed."""
    source = FileSource("test", {
        "file_path": "test_data/iq/test_tone_1khz.cf32",
        "samp_rate": 48000,
        "center_freq": 14074000,
        "loop": False
    })
    # Test decoder output, waterfall generation, etc.
```

### Generate Custom Test Signals

```bash
# Wideband FM (2.4MHz like RTL-SDR)
python test/generate_test_iq.py --signal fm --frequency 500000 \
    --sample-rate 2400000 --duration 0.5 --deviation 75000 \
    --center-freq 98100000 -o test_data/iq/wideband_fm.cf32

# AM signal
python test/generate_test_iq.py --signal am --frequency 5000 \
    --sample-rate 48000 --duration 2 -o test_data/iq/am_test.cf32
```

## Test Results

✅ **105 tests passing** (102 pass, 3 skip locally without pycsdr)
✅ **CI/CD passing** on all Python versions
✅ **IQ format validated** - Correct complex float32 structure
✅ **All signal types verified** - Tone, AM, FM, Noise working

## Dependencies

- `pv` (pipe viewer) - for rate-limited playback
- `nmux` - already required by OpenWebRX+
- `pycsdr` - already required by OpenWebRX+

## Future Enhancements

- Record real IQ files from actual SDR hardware
- Add decoder output validation tests (e.g., "FT8 file should decode X callsigns")
- Web UI playback controls (pause, seek, speed)
- Multiple file sources for band scanning simulation

## Testing

All tests pass:
```bash
# Run all tests
python -m unittest discover test -v

# Run integration tests only
python -m unittest test.test_integration_file_source test.test_file_source -v
```

## Files Changed

- `owrx/source/file.py` - FileSource implementation
- `owrx/feature.py` - Add 'file' feature detection
- `test/generate_test_iq.py` - Signal generator
- `test/test_file_source.py` - Unit tests
- `test/test_integration_file_source.py` - Integration tests
- `test/test_core_modules.py` - Core module tests
- `test_data/iq/*` - Test files and documentation
- `.github/workflows/test.yml` - CI/CD workflow
- `Dockerfile.test` - Test environment
- `docs/claude/iq-file-testing.md` - Design document

---

This enables both **automated testing in CI/CD** and **manual testing/demo mode** without requiring physical SDR hardware or waiting for real signals. Users can now explore OpenWebRX+ immediately and developers can run reproducible tests.
