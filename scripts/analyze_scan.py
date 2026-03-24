#!/usr/bin/env python3
"""Analyze scanner results: audit detections, audio quality, and classify issues.

Usage:
    # Analyze default output directory
    python3 scripts/analyze_scan.py

    # Analyze specific database and output dir
    python3 scripts/analyze_scan.py --db /tmp/scanner.db --audio-dir /tmp/scan_output

    # Show only issues
    python3 scripts/analyze_scan.py --issues-only

    # Export detections as CSV
    python3 scripts/analyze_scan.py --csv detections.csv
"""

import argparse
import csv
import os
import sqlite3
import sys
import wave
from collections import Counter
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from owrx.scanner.known_freqs import match_known_freq
from owrx.scanner.sweep import demod_mode_for_freq


def analyze_detections(db_path):
    """Analyze all detections in the database."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM detections ORDER BY timestamp").fetchall()
    sessions = db.execute("SELECT * FROM scan_sessions ORDER BY started_at").fetchall()
    bookmarks = db.execute("SELECT * FROM bookmarks").fetchall()
    db.close()

    issues = []

    print("=" * 80)
    print("SCANNER RESULTS ANALYSIS")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")
    print(f"Total detections: {len(rows)}")
    print(f"Scan sessions: {len(sessions)}")
    print(f"Bookmarks: {len(bookmarks)}")

    # --- Detection table ---
    print(f"\n{'─' * 80}")
    print("DETECTIONS")
    print(f"{'─' * 80}")
    print(f"{'#':>3} {'Freq (MHz)':>12} {'BW kHz':>7} {'SNR':>5} {'Mode':>4} "
          f"{'Expected':>4} {'Class':>7} {'Dur':>5} {'Rec':>3} {'Label'}")
    print(f"{'─' * 80}")

    freq_counts = Counter()
    mode_mismatches = []
    no_duration = 0
    no_recording = 0

    for i, r in enumerate(rows):
        freq = r["frequency_hz"]
        mode = r["mode"]
        bw = r["bandwidth_hz"] or 0
        snr = r["snr_db"] or 0
        dur = r["duration_sec"]
        rec = "YES" if r["recording_path"] else ""
        label = match_known_freq(freq) or r["bookmark_label"] or ""
        expected_mode = demod_mode_for_freq(freq)

        freq_counts[freq] += 1

        # Check mode mismatch
        mode_flag = ""
        if mode != expected_mode:
            mode_flag = "!!"
            mode_mismatches.append({
                "freq": freq, "detected": mode,
                "expected": expected_mode, "bw": bw,
            })

        dur_str = f"{dur:.1f}" if dur else "—"
        if not dur:
            no_duration += 1
        if not r["recording_path"]:
            no_recording += 1

        print(f"{i+1:>3} {freq/1e6:>12.4f} {bw/1e3:>7.1f} {snr:>5.1f} {mode:>4} "
              f"{expected_mode:>4}{mode_flag:>2} {r['classification'] or '':>7} "
              f"{dur_str:>5} {rec:>3} {label}")

    # --- Duplicates ---
    dupes = {f: c for f, c in freq_counts.items() if c > 1}
    if dupes:
        print(f"\n{'─' * 80}")
        print("DUPLICATE DETECTIONS (same freq appears multiple times)")
        print(f"{'─' * 80}")
        for freq, count in sorted(dupes.items(), key=lambda x: -x[1]):
            label = match_known_freq(freq) or ""
            print(f"  {freq/1e6:.4f} MHz — {count} times  {label}")
        issues.append(f"{len(dupes)} frequencies detected multiple times (no dedup)")

    # --- Mode mismatches ---
    if mode_mismatches:
        print(f"\n{'─' * 80}")
        print("MODE MISMATCHES (detected mode != expected for frequency band)")
        print(f"{'─' * 80}")
        for m in mode_mismatches:
            print(f"  {m['freq']/1e6:.4f} MHz: classified as '{m['detected']}' "
                  f"but band says '{m['expected']}' (BW={m['bw']/1e3:.1f} kHz)")
        issues.append(f"{len(mode_mismatches)} mode mismatches — bandwidth estimator overriding frequency band lookup")

    # --- Missing data ---
    if no_duration:
        issues.append(f"{no_duration}/{len(rows)} detections have no duration")
    if no_recording:
        issues.append(f"{no_recording}/{len(rows)} detections have no recording")

    # --- Frequency coverage ---
    print(f"\n{'─' * 80}")
    print("UNIQUE FREQUENCIES")
    print(f"{'─' * 80}")
    unique_freqs = sorted(set(r["frequency_hz"] for r in rows))
    for freq in unique_freqs:
        label = match_known_freq(freq) or "unknown"
        mode = demod_mode_for_freq(freq)
        count = freq_counts[freq]
        print(f"  {freq/1e6:.4f} MHz  ({mode})  {count}x  {label}")

    return issues, rows


def analyze_audio(audio_dir):
    """Analyze all WAV files in the output directory."""
    issues = []
    wav_files = sorted(Path(audio_dir).glob("*.wav"))

    if not wav_files:
        print(f"\nNo WAV files in {audio_dir}")
        return issues

    print(f"\n{'─' * 80}")
    print("AUDIO FILES")
    print(f"{'─' * 80}")
    print(f"{'File':>55} {'Rate':>6} {'Dur':>5} {'RMS':>7} {'Peak':>6} {'Quality'}")
    print(f"{'─' * 80}")

    for wav_path in wav_files:
        try:
            with wave.open(str(wav_path), "r") as w:
                n = w.getnframes()
                rate = w.getframerate()
                frames = w.readframes(n)
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768
                rms = np.sqrt(np.mean(audio ** 2))
                peak = np.max(np.abs(audio))
                dur = n / rate

                # Quality assessment
                quality_issues = []
                if rms < 0.01:
                    quality_issues.append("SILENT")
                elif rms < 0.03:
                    quality_issues.append("very quiet")
                if peak > 0.99:
                    quality_issues.append("CLIPPED")
                if rms > 0.4:
                    quality_issues.append("too loud")
                if rate not in (8000, 11025, 16000, 22050, 44100, 48000, 96000):
                    quality_issues.append(f"odd rate")

                # Check for DC offset
                dc = abs(np.mean(audio))
                if dc > 0.01:
                    quality_issues.append(f"DC offset={dc:.3f}")

                # Check dynamic range (std dev of RMS over 0.5s windows)
                if dur > 1.0:
                    window = rate // 2
                    rms_windows = []
                    for start in range(0, len(audio) - window, window):
                        chunk = audio[start:start + window]
                        rms_windows.append(np.sqrt(np.mean(chunk ** 2)))
                    rms_std = np.std(rms_windows)
                    if rms_std < 0.005 and rms > 0.05:
                        quality_issues.append("flat (no dynamics)")

                quality = ", ".join(quality_issues) if quality_issues else "OK"
                if quality_issues:
                    issues.append(f"{wav_path.name}: {quality}")

                print(f"{wav_path.name:>55} {rate:>6} {dur:>5.1f} {rms:>7.4f} "
                      f"{peak:>6.3f} {quality}")

        except Exception as e:
            print(f"{wav_path.name:>55} ERROR: {e}")
            issues.append(f"{wav_path.name}: failed to read ({e})")

    return issues


def analyze_sessions(db_path):
    """Show scan session history."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    sessions = db.execute("SELECT * FROM scan_sessions ORDER BY started_at").fetchall()
    db.close()

    if not sessions:
        return

    print(f"\n{'─' * 80}")
    print("SCAN SESSIONS")
    print(f"{'─' * 80}")
    for s in sessions:
        started = s["started_at"]
        stopped = s["stopped_at"] or "running"
        config = s["config_json"]
        print(f"  #{s['id']} started={started} stopped={stopped}")
        if config:
            import json
            try:
                c = json.loads(config)
                if "files" in c:
                    for f in c["files"]:
                        print(f"       file: {Path(f).name}")
                if "freq_start" in c:
                    print(f"       range: {c['freq_start']/1e6:.0f}-{c.get('freq_stop', 0)/1e6:.0f} MHz")
            except (json.JSONDecodeError, TypeError):
                pass


def print_summary(all_issues):
    """Print summary of all issues found."""
    print(f"\n{'=' * 80}")
    print("ISSUES SUMMARY")
    print(f"{'=' * 80}")
    if all_issues:
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("  No issues found!")
    print()


def export_csv(db_path, csv_path):
    """Export detections to CSV."""
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    rows = db.execute("SELECT * FROM detections ORDER BY timestamp").fetchall()
    db.close()

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "id", "timestamp", "frequency_mhz", "bandwidth_khz", "mode",
            "expected_mode", "peak_power_db", "snr_db", "duration_sec",
            "classification", "filter_result", "known_label",
            "has_recording",
        ])
        for r in rows:
            freq = r["frequency_hz"]
            writer.writerow([
                r["id"],
                r["timestamp"],
                f"{freq/1e6:.4f}",
                f"{(r['bandwidth_hz'] or 0)/1e3:.1f}",
                r["mode"],
                demod_mode_for_freq(freq),
                f"{r['peak_power_db']:.1f}" if r["peak_power_db"] else "",
                f"{r['snr_db']:.1f}" if r["snr_db"] else "",
                f"{r['duration_sec']:.1f}" if r["duration_sec"] else "",
                r["classification"],
                r["filter_result"],
                match_known_freq(freq) or "",
                "yes" if r["recording_path"] else "",
            ])
    print(f"\nExported {len(rows)} detections to {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze scanner results: detections, audio quality, issues.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", default=None,
                        help="Scanner database path (default: test_data/output/scanner.db)")
    parser.add_argument("--audio-dir", default=None,
                        help="Directory with WAV files (default: test_data/output)")
    parser.add_argument("--issues-only", action="store_true",
                        help="Only print the issues summary")
    parser.add_argument("--csv", default=None,
                        help="Export detections to CSV file")

    args = parser.parse_args()

    default_output = str(PROJECT_ROOT / "test_data" / "output")
    db_path = args.db or os.path.join(default_output, "scanner.db")
    audio_dir = args.audio_dir or default_output

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        print(f"Run 'python3 scripts/scan_iq.py test_data/iq/*.cf32' first.")
        sys.exit(1)

    all_issues = []

    if args.csv:
        export_csv(db_path, args.csv)
        return

    if args.issues_only:
        det_issues, _ = analyze_detections(db_path)
        audio_issues = analyze_audio(audio_dir)
        all_issues = det_issues + audio_issues
        print_summary(all_issues)
        return

    det_issues, rows = analyze_detections(db_path)
    all_issues.extend(det_issues)

    analyze_sessions(db_path)

    audio_issues = analyze_audio(audio_dir)
    all_issues.extend(audio_issues)

    print_summary(all_issues)


if __name__ == "__main__":
    main()
