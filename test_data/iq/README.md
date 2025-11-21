# IQ Test Data Files

This directory contains IQ recording files for automated testing and demo mode.

## File Format

- **Format:** Complex Float 32-bit (`.cf32`)
- **Structure:** Interleaved I/Q samples, 8 bytes per sample
- **Metadata:** JSON sidecar files with same basename

## Recording IQ Files

### Using rtl_sdr
```bash
# Record raw unsigned 8-bit
rtl_sdr -f 14074000 -s 48000 -g 40 recording.cu8

# Convert to cf32
csdr convert_u8_f < recording.cu8 > recording.cf32
```

### Using hackrf_transfer
```bash
hackrf_transfer -r recording.cs8 -f 14074000 -s 2000000
# Convert signed 8-bit to cf32
csdr convert_s8_f < recording.cs8 > recording.cf32
```

## Metadata Format

Each `.cf32` file should have a corresponding `.json` file:

```json
{
  "sample_rate": 48000,
  "center_frequency": 14074000,
  "description": "FT8 signals on 20m band",
  "duration_seconds": 60,
  "expected_decodes": ["CQ DX1ABC PM95"]
}
```

## Test Files (to be added)

- `ft8_14074khz_48k.cf32` - FT8 on 20m
- `fm_broadcast_*.cf32` - FM with RDS
- `aprs_144390khz_48k.cf32` - APRS packets

## Usage

Configure a FileSource in OpenWebRX+ settings:

```yaml
sdrs:
  demo:
    type: file
    name: "Demo (FT8 Recording)"
    file_path: "/path/to/test_data/iq/ft8_14074khz_48k.cf32"
    profiles:
      ft8:
        name: "20m FT8"
        center_freq: 14074000
        samp_rate: 48000
```
