#!/usr/bin/env python3
"""Scan IQ files: detect signals, classify, log to DB, demodulate to WAV.

Usage:
    # Scan a single IQ file (reads metadata from .json sidecar)
    python3 scripts/scan_iq.py test_data/iq/koin_443_150_60sec.cf32

    # Scan with explicit parameters
    python3 scripts/scan_iq.py test_data/iq/koin_443_150_60sec.cf32 \\
        --center-freq 443150000 --sample-rate 2400000

    # Scan multiple files
    python3 scripts/scan_iq.py test_data/iq/*.cf32

    # Scan with custom output directory and database
    python3 scripts/scan_iq.py test_data/iq/*.cf32 \\
        --output-dir /tmp/scan_output \\
        --db /tmp/scanner.db

    # Demod a specific frequency (not just the strongest)
    python3 scripts/scan_iq.py test_data/iq/noaa_all_1mhz_15sec.cf32 \\
        --center-freq 162475000 --sample-rate 1000000 \\
        --demod-freq 162550000

    # Demod ALL detected signals (not just the strongest)
    python3 scripts/scan_iq.py test_data/iq/fm_band_wide_6mhz_10sec.cf32 \\
        --center-freq 97000000 --sample-rate 6000000 --demod-all
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from owrx.scanner.classifier import ClassificationPipeline
from owrx.scanner.db import ScannerDatabase
from owrx.scanner.detector import SignalDetector
from owrx.scanner.dsp import demod_am, demod_fm, extract_channel, save_wav
from owrx.scanner.known_freqs import match_known_freq
from owrx.scanner.sweep import demod_mode_for_freq


# ---------- IQ loading ----------

def load_iq(path):
    """Load CF32 IQ file. Returns complex64 array."""
    iq = np.fromfile(path, dtype=np.complex64)
    return iq


def load_metadata(iq_path):
    """Load JSON sidecar metadata for an IQ file."""
    meta_path = Path(iq_path).with_suffix(".json")
    if meta_path.exists():
        with open(meta_path) as f:
            return json.load(f)
    return {}


# ---------- Scan pipeline ----------

def scan_iq_file(iq_path, center_freq, sample_rate, db, output_dir,
                 demod_freq=None, demod_all=False,
                 snr_threshold=8.0, merge_gap=15):
    """Run the full scan pipeline on one IQ file.

    Returns list of detection result dicts.
    """
    name = Path(iq_path).stem
    iq = load_iq(iq_path)
    duration = len(iq) / sample_rate

    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"  {center_freq/1e6:.3f} MHz center, {sample_rate/1e6:.1f} MS/s, {duration:.1f} sec")
    print(f"{'=' * 60}")

    # Detect
    detector = SignalDetector(
        fft_size=4096, sample_rate=sample_rate,
        snr_threshold_db=snr_threshold, merge_gap_bins=merge_gap,
    )
    signals = detector.detect_from_iq(iq[:4096 * 32], center_freq, num_averages=32)
    classifier = ClassificationPipeline()

    print(f"\n  {len(signals)} signal(s) detected:")
    results = []
    for i, sig in enumerate(signals):
        cls = classifier.classify(
            frequency_hz=int(sig["frequency_hz"]),
            bandwidth_hz=sig["bandwidth_hz"],
            peak_power_db=sig["peak_power_db"],
            snr_db=sig["snr_db"],
        )

        det_id = db.log_detection(
            frequency_hz=int(sig["frequency_hz"]),
            bandwidth_hz=int(sig["bandwidth_hz"]),
            mode=cls["mode"],
            peak_power_db=sig["peak_power_db"],
            snr_db=sig["snr_db"],
            classification=cls["classification"],
            filter_result=cls["filter_result"],
        )

        known_label = match_known_freq(sig["frequency_hz"]) or ""
        label_suffix = f"  [{known_label}]" if known_label else ""
        print(f"  [{i+1}] {sig['frequency_hz']/1e6:.4f} MHz  "
              f"BW={sig['bandwidth_hz']/1e3:.1f}kHz  "
              f"SNR={sig['snr_db']:.1f}dB  "
              f"mode={cls['mode']}  "
              f"action={cls['action']}{label_suffix}")

        results.append({
            "det_id": det_id,
            "signal": sig,
            "classification": cls,
        })

    # Decide what to demod
    to_demod = []
    if demod_freq:
        # Demod a specific frequency
        mode = demod_mode_for_freq(demod_freq)
        to_demod.append({"frequency_hz": demod_freq, "mode": mode, "label": "manual"})
    elif demod_all and results:
        # Demod every detected signal
        for r in results:
            to_demod.append({
                "frequency_hz": r["signal"]["frequency_hz"],
                "mode": r["classification"]["mode"],
                "label": f"{r['signal']['frequency_hz']/1e6:.4f}mhz",
            })
    elif results:
        # Demod the strongest
        r = results[0]
        to_demod.append({
            "frequency_hz": r["signal"]["frequency_hz"],
            "mode": r["classification"]["mode"],
            "label": "strongest",
        })

    # Demod
    os.makedirs(output_dir, exist_ok=True)
    wav_files_produced = []
    for d in to_demod:
        freq = d["frequency_hz"]
        mode = d["mode"]

        if mode == "wfm":
            channel_bw, deviation, target_rate = 200000, 75000, 48000
        elif mode == "nfm":
            channel_bw, deviation, target_rate = 16000, 5000, 16000
        elif mode == "am":
            channel_bw, deviation, target_rate = 10000, 0, 16000
        else:
            channel_bw, deviation, target_rate = 16000, 5000, 16000

        ch_iq, ch_rate = extract_channel(
            iq, center_freq, freq, sample_rate, channel_bw,
            target_rate=target_rate,
        )

        if mode in ("wfm", "nfm"):
            audio = demod_fm(ch_iq, ch_rate, deviation)
        else:
            audio = demod_am(ch_iq)

        final_rate = ch_rate

        wav_name = f"{name}_{freq/1e6:.4f}mhz_{mode}.wav"
        wav_path = os.path.join(output_dir, wav_name)
        save_wav(wav_path, audio, final_rate)
        wav_files_produced.append(wav_path)

        duration_sec = len(audio) / final_rate
        print(f"\n  Demod: {freq/1e6:.4f} MHz ({mode}) -> {wav_name}")
        print(f"         {final_rate} Hz, {duration_sec:.1f} sec, {os.path.getsize(wav_path)//1024} KB")

        # Update DB with recording path
        for r in results:
            if abs(r["signal"]["frequency_hz"] - freq) < 1000:
                db.update_detection(r["det_id"],
                                    recording_path=wav_path,
                                    duration_sec=duration_sec)
                break

    return results, wav_files_produced


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description="Scan IQ files: detect signals, classify, log to DB, demodulate to WAV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("iq_files", nargs="+", help="CF32 IQ file(s) to scan")
    parser.add_argument("--center-freq", "-f", type=float, default=None,
                        help="Center frequency in Hz (reads from .json sidecar if omitted)")
    parser.add_argument("--sample-rate", "-s", type=float, default=None,
                        help="Sample rate in Hz (reads from .json sidecar if omitted)")
    parser.add_argument("--output-dir", "-o", default=None,
                        help="Output directory for WAV files (default: test_data/output)")
    parser.add_argument("--db", default=None,
                        help="SQLite database path (default: <output-dir>/scanner.db)")
    parser.add_argument("--demod-freq", type=float, default=None,
                        help="Demodulate a specific frequency instead of the strongest")
    parser.add_argument("--demod-all", action="store_true",
                        help="Demodulate ALL detected signals, not just the strongest")
    parser.add_argument("--snr-threshold", type=float, default=8.0,
                        help="SNR threshold in dB for signal detection (default: 8.0)")
    parser.add_argument("--merge-gap", type=int, default=15,
                        help="FFT bins gap for merging adjacent signals (default: 15)")

    args = parser.parse_args()

    output_dir = args.output_dir or str(PROJECT_ROOT / "test_data" / "output")
    os.makedirs(output_dir, exist_ok=True)
    db_path = args.db or os.path.join(output_dir, "scanner.db")

    db = ScannerDatabase(db_path)
    session_id = db.start_session(config={
        "files": [str(f) for f in args.iq_files],
        "snr_threshold": args.snr_threshold,
    })

    total_detections = 0
    total_files = 0
    all_wav_files = []

    for iq_file in args.iq_files:
        if not os.path.exists(iq_file):
            print(f"SKIP: {iq_file} (not found)")
            continue

        meta = load_metadata(iq_file)
        center_freq = args.center_freq or meta.get("center_freq_hz")
        sample_rate = args.sample_rate or meta.get("sample_rate")

        if not center_freq or not sample_rate:
            print(f"SKIP: {iq_file} (no center_freq or sample_rate — use --center-freq and --sample-rate, or provide .json sidecar)")
            continue

        results, wav_files = scan_iq_file(
            iq_file, center_freq, sample_rate, db, output_dir,
            demod_freq=args.demod_freq, demod_all=args.demod_all,
            snr_threshold=args.snr_threshold, merge_gap=args.merge_gap,
        )
        total_detections += len(results)
        total_files += 1
        all_wav_files.extend(wav_files)

    db.stop_session(session_id)
    db.close()

    print(f"\n{'=' * 60}")
    print(f"  Scanned {total_files} file(s), {total_detections} signal(s) detected")
    print(f"  Database: {db_path}")
    print(f"  Audio:    {output_dir}/")
    print(f"{'=' * 60}")

    # Print playback commands for files produced THIS run only
    if all_wav_files:
        print("\nPlay:")
        for w in all_wav_files[-5:]:
            print(f"  ffplay -nodisp -autoexit {w}")


if __name__ == "__main__":
    main()
