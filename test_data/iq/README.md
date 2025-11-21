# IQ Test Data Files

This directory contains IQ recording files for automated testing and demo mode.

## File Format

- **Format:** Complex Float 32-bit (`.cf32`)
- **Structure:** Interleaved I/Q samples, 8 bytes per sample
- **Metadata:** JSON sidecar files with same basename

## Included Test Files

| File | Sample Rate | Description |
|------|-------------|-------------|
| `test_tone_1khz.cf32` | 48 kHz | 1kHz tone for basic testing |
| `test_fm_240k.cf32` | 240 kHz | FM signal with 75kHz deviation |

## Generating Synthetic Test Files

Use the included generator script:

```bash
# Simple tone
python test/generate_test_iq.py --signal tone --frequency 1000 \
    --sample-rate 48000 --duration 2 -o test_data/iq/my_tone.cf32

# FM broadcast signal (240kHz sample rate)
python test/generate_test_iq.py --signal fm --frequency 100000 \
    --sample-rate 240000 --duration 1 --deviation 75000 \
    --center-freq 98100000 -o test_data/iq/fm_test.cf32

# Wideband FM (2.4MHz like RTL-SDR) - WARNING: Large files!
python test/generate_test_iq.py --signal fm --frequency 500000 \
    --sample-rate 2400000 --duration 0.5 --deviation 75000 \
    --center-freq 98100000 -o test_data/iq/wideband_fm.cf32

# AM signal
python test/generate_test_iq.py --signal am --frequency 5000 \
    --sample-rate 48000 --duration 2 -o test_data/iq/am_test.cf32
```

### File Size Reference

| Sample Rate | 1 second | 10 seconds |
|-------------|----------|------------|
| 48 kHz | 384 KB | 3.8 MB |
| 240 kHz | 1.9 MB | 19 MB |
| 2.4 MHz | 19 MB | 192 MB |

## Recording Real IQ Files

### Using rtl_sdr
```bash
# Record raw unsigned 8-bit
rtl_sdr -f 98100000 -s 2400000 -g 40 recording.cu8

# Convert to cf32
csdr convert_u8_f < recording.cu8 > recording.cf32
```

### Using hackrf_transfer
```bash
hackrf_transfer -r recording.cs8 -f 98100000 -s 2000000
# Convert signed 8-bit to cf32
csdr convert_s8_f < recording.cs8 > recording.cf32
```

## Metadata Format

Each `.cf32` file should have a corresponding `.json` file:

```json
{
  "sample_rate": 240000,
  "center_frequency": 98100000,
  "description": "FM broadcast signal",
  "duration_seconds": 1.0,
  "signal_type": "fm"
}
```

## Usage with FileSource

Configure a FileSource in OpenWebRX+ settings:

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
