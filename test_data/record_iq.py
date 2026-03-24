#!/usr/bin/env python3
"""Record IQ files from SDRplay RSP1a across different bands.

Each recording captures a few seconds of complex float32 IQ data
at a given center frequency and sample rate. Saves as .cf32 files
with JSON sidecar metadata.

Usage: python3 test_data/record_iq.py
"""

import json
import os
import subprocess
import sys
import time

# Recording parameters: (name, center_freq_hz, sample_rate, duration_sec, gain)
RECORDINGS = [
    # FM Broadcast — should have strong signals
    ("fm_broadcast_97_5mhz", 97500000, 2400000, 3, 29),
    ("fm_broadcast_91_5mhz", 91500000, 2400000, 3, 29),

    # NOAA Weather Radio — 162.475 MHz (Portland primary KIG77)
    ("noaa_weather_162mhz", 162475000, 2400000, 5, 40),

    # Air Band — 121.5 MHz emergency + Portland approach
    ("airband_121mhz", 121500000, 2400000, 5, 40),
    ("airband_portland_approach", 124000000, 2400000, 5, 40),

    # 2m Ham — 146.520 national simplex
    ("ham_2m_146mhz", 146520000, 2400000, 5, 40),

    # GMRS/FRS — 462 MHz
    ("gmrs_462mhz", 462562500, 2400000, 5, 40),

    # Marine VHF — Ch 16 (156.800 MHz)
    ("marine_vhf_ch16", 156800000, 2400000, 5, 40),

    # Wideband FM sweep — wider sample rate to capture multiple stations
    ("fm_broadcast_wide_6mhz", 97500000, 6000000, 3, 29),

    # Noise floor reference — frequency with no expected signals
    ("noise_floor_450mhz", 450000000, 2400000, 3, 40),

    # HF CB — 27 MHz
    ("hf_cb_27mhz", 27000000, 2400000, 3, 40),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "iq")


def record_iq(name, center_freq, sample_rate, duration_sec, gain):
    """Record IQ data using SoapySDRUtil --args and rx_sdr or SoapySDR Python."""
    output_path = os.path.join(OUTPUT_DIR, f"{name}.cf32")
    meta_path = os.path.join(OUTPUT_DIR, f"{name}.json")

    num_samples = sample_rate * duration_sec
    num_bytes = num_samples * 8  # complex float32 = 8 bytes per sample

    print(f"\n{'='*60}")
    print(f"Recording: {name}")
    print(f"  Freq: {center_freq/1e6:.3f} MHz, Rate: {sample_rate/1e6:.1f} MS/s")
    print(f"  Duration: {duration_sec}s, Gain: {gain}")
    print(f"  Output: {output_path}")

    # Use SoapySDRUtil --args to stream IQ to file
    # SoapySDRUtil doesn't have a record mode, so use Python SoapySDR
    try:
        import SoapySDR
        from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
        import numpy as np

        # Open device
        args = {"driver": "sdrplay"}
        sdr = SoapySDR.Device(args)

        # Configure
        sdr.setSampleRate(SOAPY_SDR_RX, 0, sample_rate)
        sdr.setFrequency(SOAPY_SDR_RX, 0, center_freq)
        sdr.setGainMode(SOAPY_SDR_RX, 0, False)  # manual gain
        sdr.setGain(SOAPY_SDR_RX, 0, "IFGR", gain)

        # Setup stream
        stream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
        sdr.activateStream(stream)

        # Record
        chunk_size = min(65536, sample_rate)
        samples_remaining = num_samples
        all_samples = []

        start_time = time.time()
        while samples_remaining > 0:
            buf = np.zeros(min(chunk_size, samples_remaining), dtype=np.complex64)
            sr = sdr.readStream(stream, [buf], len(buf))
            if sr.ret > 0:
                all_samples.append(buf[:sr.ret].copy())
                samples_remaining -= sr.ret

        elapsed = time.time() - start_time

        # Deactivate and close
        sdr.deactivateStream(stream)
        sdr.closeStream(stream)
        sdr.close = None  # SoapySDR doesn't have explicit close

        # Save
        iq_data = np.concatenate(all_samples)
        iq_data.tofile(output_path)

        # Save metadata
        meta = {
            "name": name,
            "center_freq_hz": center_freq,
            "sample_rate": sample_rate,
            "duration_sec": duration_sec,
            "actual_duration_sec": round(elapsed, 2),
            "num_samples": len(iq_data),
            "gain": gain,
            "format": "cf32",
            "device": "SDRplay RSP1a",
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "file_size_bytes": os.path.getsize(output_path),
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        size_mb = os.path.getsize(output_path) / 1e6
        print(f"  Saved: {len(iq_data)} samples, {size_mb:.1f} MB, {elapsed:.1f}s")
        return True

    except ImportError:
        print("  SoapySDR Python bindings not available, skipping")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Recording {len(RECORDINGS)} IQ files to {OUTPUT_DIR}")
    print(f"Device: SDRplay RSP1a")

    success = 0
    failed = 0

    for name, freq, rate, dur, gain in RECORDINGS:
        if record_iq(name, freq, rate, dur, gain):
            success += 1
        else:
            failed += 1

    print(f"\n{'='*60}")
    print(f"Done: {success} recorded, {failed} failed")
    print(f"Files in: {OUTPUT_DIR}")

    # List files
    for f in sorted(os.listdir(OUTPUT_DIR)):
        path = os.path.join(OUTPUT_DIR, f)
        if f.endswith(".cf32"):
            size_mb = os.path.getsize(path) / 1e6
            print(f"  {f}: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
