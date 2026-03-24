"""End-to-end scanner integration test.

Loads real IQ recordings, runs the full scanner pipeline
(detect -> classify -> log to DB -> demodulate -> WAV output),
and produces listenable audio files.

Works both as a pytest test and as a standalone script.
"""

import json
import os
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import decimate as scipy_decimate

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from owrx.scanner.classifier import ClassificationPipeline
from owrx.scanner.db import ScannerDatabase
from owrx.scanner.detector import SignalDetector

IQ_DIR = PROJECT_ROOT / "test_data" / "iq"
OUTPUT_DIR = PROJECT_ROOT / "test_data" / "output"

# ---------- DSP helpers ----------


def extract_channel(
    iq: np.ndarray,
    center_freq: float,
    signal_freq: float,
    sample_rate: float,
    channel_bw: float,
) -> np.ndarray:
    """Shift signal to baseband and decimate."""
    offset = signal_freq - center_freq
    t = np.arange(len(iq)) / sample_rate
    shifted = iq * np.exp(-1j * 2 * np.pi * offset * t)

    decimation = max(1, int(sample_rate / channel_bw))
    decimated_i = scipy_decimate(shifted.real, decimation)
    decimated_q = scipy_decimate(shifted.imag, decimation)
    return decimated_i + 1j * decimated_q


def demod_fm(iq: np.ndarray) -> np.ndarray:
    """FM demodulate via phase differentiation."""
    phase = np.angle(iq)
    dphase = np.diff(np.unwrap(phase))
    audio = dphase / np.pi
    return np.clip(audio, -1.0, 1.0)


def demod_am(iq: np.ndarray) -> np.ndarray:
    """AM demodulate via envelope detection."""
    envelope = np.abs(iq)
    audio = envelope - np.mean(envelope)
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak
    return audio


def save_wav(filename: str, audio: np.ndarray, sample_rate: int) -> None:
    """Save float audio as 16-bit mono WAV."""
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


# ---------- IQ file loading ----------


def load_iq_file(name: str) -> tuple[np.ndarray, dict]:
    """Load a CF32 IQ file and its JSON metadata.

    Returns (iq_samples, metadata_dict).
    """
    iq_path = IQ_DIR / f"{name}.cf32"
    meta_path = IQ_DIR / f"{name}.json"
    if not iq_path.exists():
        raise FileNotFoundError(f"IQ file not found: {iq_path}")

    iq = np.fromfile(str(iq_path), dtype=np.float32)
    # Interleaved float32 -> complex64
    iq = iq[0 : len(iq) // 2 * 2]  # ensure even length
    iq = iq[0::2] + 1j * iq[1::2]

    meta = {}
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)

    return iq, meta


# ---------- Full pipeline ----------


def run_scanner_on_iq(
    iq_name: str,
    center_freq: float,
    sample_rate: float,
    db_path: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """Run the full scanner pipeline on an IQ recording.

    Returns a results dict with detections, classifications, and audio paths.
    """
    iq, meta = load_iq_file(iq_name)

    # 1. Detect signals
    detector = SignalDetector(
        fft_size=4096,
        sample_rate=sample_rate,
        snr_threshold_db=8.0,
        merge_gap_bins=15,
    )
    detections = detector.detect_from_iq(iq, center_freq, num_averages=16)

    # 2. Classify each signal
    classifier = ClassificationPipeline()
    classifications = []
    for det in detections:
        cls = classifier.classify(
            frequency_hz=int(det["frequency_hz"]),
            bandwidth_hz=det["bandwidth_hz"],
            peak_power_db=det["peak_power_db"],
            snr_db=det["snr_db"],
        )
        classifications.append(cls)

    # 3. Log to database
    close_db = False
    if db_path:
        db = ScannerDatabase(db_path)
        close_db = True
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        tmp.close()
        db = ScannerDatabase(tmp.name)
        db_path = tmp.name
        close_db = True

    detection_ids = []
    for det, cls in zip(detections, classifications):
        det_id = db.log_detection(
            frequency_hz=int(det["frequency_hz"]),
            bandwidth_hz=int(det["bandwidth_hz"]),
            mode=cls["mode"],
            peak_power_db=det["peak_power_db"],
            snr_db=det["snr_db"],
            classification=cls["classification"],
            filter_result=cls["filter_result"],
        )
        detection_ids.append(det_id)

    # 4. Demodulate the strongest signal (if any)
    audio_path = None
    audio_sample_rate = None
    demod_info = None

    if detections:
        strongest = detections[0]  # already sorted by power
        strongest_cls = classifications[0]
        mode = strongest_cls["mode"]

        # Choose channel bandwidth and target audio rate
        if mode == "wfm":
            channel_bw = 200_000
            audio_rate = 48_000
        elif mode == "nfm":
            channel_bw = 16_000
            audio_rate = 16_000
        elif mode == "am":
            channel_bw = 10_000
            audio_rate = 10_000
        else:
            channel_bw = 16_000
            audio_rate = 16_000

        # Extract channel
        channel_iq = extract_channel(
            iq, center_freq, strongest["frequency_hz"], sample_rate, channel_bw
        )
        actual_rate = sample_rate / max(1, int(sample_rate / channel_bw))

        # Demodulate
        if mode in ("wfm", "nfm"):
            audio = demod_fm(channel_iq)
        else:
            audio = demod_am(channel_iq)

        # Final decimation to target audio rate if needed
        if actual_rate > audio_rate * 1.5:
            final_dec = max(1, int(actual_rate / audio_rate))
            audio = scipy_decimate(audio, final_dec)
            actual_rate = actual_rate / final_dec

        audio_sample_rate = int(actual_rate)

        # Save WAV
        out_dir = output_dir or str(OUTPUT_DIR)
        os.makedirs(out_dir, exist_ok=True)
        wav_name = f"{iq_name}_demod.wav"
        audio_path = os.path.join(out_dir, wav_name)
        save_wav(audio_path, audio, audio_sample_rate)

        # Update DB with recording path
        if detection_ids:
            db.update_detection(detection_ids[0], recording_path=audio_path)

        demod_info = {
            "frequency_hz": strongest["frequency_hz"],
            "mode": mode,
            "channel_bw": channel_bw,
            "audio_sample_rate": audio_sample_rate,
            "audio_duration_sec": len(audio) / audio_sample_rate,
            "audio_samples": len(audio),
        }

    stored = db.get_recent_detections(limit=50)
    if close_db:
        db.close()

    return {
        "iq_name": iq_name,
        "center_freq": center_freq,
        "sample_rate": sample_rate,
        "num_detections": len(detections),
        "detections": detections,
        "classifications": classifications,
        "detection_ids": detection_ids,
        "db_path": db_path,
        "stored_detections": stored,
        "audio_path": audio_path,
        "audio_sample_rate": audio_sample_rate,
        "demod_info": demod_info,
    }


# ---------- Pytest tests ----------


def iq_available(name: str) -> bool:
    return (IQ_DIR / f"{name}.cf32").exists()


@pytest.mark.skipif(
    not iq_available("fm_broadcast_97mhz"),
    reason="IQ file fm_broadcast_97mhz.cf32 not present",
)
def test_fm_broadcast_full_pipeline(tmp_path):
    """Load FM broadcast IQ, detect signals, classify, demod WFM, save WAV."""
    result = run_scanner_on_iq(
        iq_name="fm_broadcast_97mhz",
        center_freq=97_500_000,
        sample_rate=2_400_000,
        db_path=str(tmp_path / "scanner.sqlite3"),
        output_dir=str(OUTPUT_DIR),
    )

    # Should detect at least one signal
    assert result["num_detections"] >= 1, "Expected at least 1 FM signal"

    # Strongest should be classified as WFM
    assert result["classifications"][0]["mode"] == "wfm"
    assert result["classifications"][0]["classification"] == "analog"

    # Audio file should exist and be non-empty
    assert result["audio_path"] is not None
    assert os.path.exists(result["audio_path"])
    assert os.path.getsize(result["audio_path"]) > 1000

    # DB should have stored all detections
    assert len(result["stored_detections"]) == result["num_detections"]

    # Demod info should be present
    assert result["demod_info"]["mode"] == "wfm"
    assert result["demod_info"]["audio_duration_sec"] > 0.5


@pytest.mark.skipif(
    not iq_available("noaa_weather_162mhz"),
    reason="IQ file noaa_weather_162mhz.cf32 not present",
)
def test_noaa_weather_full_pipeline(tmp_path):
    """Load NOAA weather IQ, detect signals, classify, demod NFM, save WAV."""
    result = run_scanner_on_iq(
        iq_name="noaa_weather_162mhz",
        center_freq=162_475_000,
        sample_rate=2_400_000,
        db_path=str(tmp_path / "scanner.sqlite3"),
        output_dir=str(OUTPUT_DIR),
    )

    # Should detect at least one signal
    assert result["num_detections"] >= 1, "Expected at least 1 NOAA signal"

    # Should be classified as NFM (NOAA weather is narrowband FM)
    assert result["classifications"][0]["mode"] == "nfm"

    # Audio file should exist
    assert result["audio_path"] is not None
    assert os.path.exists(result["audio_path"])
    assert os.path.getsize(result["audio_path"]) > 1000

    # DB check
    assert len(result["stored_detections"]) == result["num_detections"]

    # Audio duration should be reasonable (5 sec recording)
    assert result["demod_info"]["audio_duration_sec"] > 1.0


@pytest.mark.skipif(
    not iq_available("noise_floor_450mhz"),
    reason="IQ file noise_floor_450mhz.cf32 not present",
)
def test_noise_floor_no_audio(tmp_path):
    """Load noise floor IQ, expect no detections and no audio output."""
    result = run_scanner_on_iq(
        iq_name="noise_floor_450mhz",
        center_freq=450_000_000,
        sample_rate=2_400_000,
        db_path=str(tmp_path / "scanner.sqlite3"),
        output_dir=str(tmp_path / "output"),
    )

    # Should detect no signals (or very few spurious ones)
    assert result["num_detections"] <= 2, (
        f"Expected 0-2 detections in noise, got {result['num_detections']}"
    )

    # If no detections, no audio
    if result["num_detections"] == 0:
        assert result["audio_path"] is None
        assert result["demod_info"] is None


# ---------- Standalone report ----------


def format_freq(hz: float) -> str:
    """Format frequency in MHz."""
    return f"{hz / 1e6:.3f} MHz"


def print_report(results: list[dict], report_path: str | None = None) -> str:
    """Print and optionally save a text report of scanner results."""
    lines = []
    lines.append("=" * 70)
    lines.append("SCANNER E2E TEST REPORT")
    lines.append("=" * 70)

    for r in results:
        lines.append("")
        lines.append(f"--- {r['iq_name']} ---")
        lines.append(f"  Center: {format_freq(r['center_freq'])}")
        lines.append(f"  Sample rate: {r['sample_rate'] / 1e6:.1f} MS/s")
        lines.append(f"  Signals detected: {r['num_detections']}")

        for i, (det, cls) in enumerate(
            zip(r["detections"], r["classifications"])
        ):
            lines.append(
                f"  [{i+1}] {format_freq(det['frequency_hz'])}  "
                f"BW={det['bandwidth_hz']/1e3:.1f}kHz  "
                f"SNR={det['snr_db']:.1f}dB  "
                f"Power={det['peak_power_db']:.1f}dB  "
                f"Mode={cls['mode']}  "
                f"Action={cls['action']}"
            )

        if r["demod_info"]:
            d = r["demod_info"]
            lines.append(f"  Demodulated: {format_freq(d['frequency_hz'])} ({d['mode']})")
            lines.append(
                f"  Audio: {d['audio_sample_rate']} Hz, "
                f"{d['audio_duration_sec']:.2f} sec, "
                f"{d['audio_samples']} samples"
            )

        if r["audio_path"]:
            lines.append(f"  WAV: {r['audio_path']}")

        lines.append(f"  DB: {r['db_path']} ({len(r['stored_detections'])} records)")

    lines.append("")
    lines.append("=" * 70)

    report = "\n".join(lines)
    print(report)

    if report_path:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {report_path}")

    return report


def main():
    """Run all tests as a standalone script and print a report."""
    os.makedirs(str(OUTPUT_DIR), exist_ok=True)

    db_path = str(OUTPUT_DIR / "scanner_e2e.sqlite3")
    results = []

    test_cases = [
        ("fm_broadcast_97mhz", 97_500_000, 2_400_000),
        ("noaa_weather_162mhz", 162_475_000, 2_400_000),
        ("noise_floor_450mhz", 450_000_000, 2_400_000),
    ]

    for iq_name, center_freq, sample_rate in test_cases:
        if not iq_available(iq_name):
            print(f"SKIP: {iq_name} (IQ file not found)")
            continue

        print(f"Processing {iq_name}...")
        result = run_scanner_on_iq(
            iq_name=iq_name,
            center_freq=center_freq,
            sample_rate=sample_rate,
            db_path=db_path,
            output_dir=str(OUTPUT_DIR),
        )
        results.append(result)

    report_path = str(OUTPUT_DIR / "scanner_report.txt")
    print_report(results, report_path)

    # Print playback hints
    print("\nTo play audio files:")
    for r in results:
        if r["audio_path"] and os.path.exists(r["audio_path"]):
            print(f"  ffplay -nodisp -autoexit {r['audio_path']}")
            print(f"  aplay {r['audio_path']}")


if __name__ == "__main__":
    main()
