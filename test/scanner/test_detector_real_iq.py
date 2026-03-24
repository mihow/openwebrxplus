import json
from pathlib import Path

import numpy as np
import pytest

from owrx.scanner.detector import SignalDetector

IQ_DIR = Path(__file__).resolve().parent.parent.parent / "test_data" / "iq"


def _load_iq(name: str) -> tuple[np.ndarray, dict]:
    """Load CF32 IQ recording and its JSON metadata. Returns (samples, meta)."""
    cf32_path = IQ_DIR / f"{name}.cf32"
    json_path = IQ_DIR / f"{name}.json"
    if not cf32_path.exists():
        pytest.skip(f"IQ file not found: {cf32_path}")
    samples = np.fromfile(str(cf32_path), dtype=np.complex64)
    with open(json_path) as f:
        meta = json.load(f)
    return samples, meta


def _make_detector(meta: dict, **kwargs) -> SignalDetector:
    """Create a SignalDetector from recording metadata."""
    defaults = dict(
        fft_size=4096,
        sample_rate=meta["sample_rate"],
        snr_threshold_db=10.0,
    )
    defaults.update(kwargs)
    return SignalDetector(**defaults)


class TestFmBroadcast:
    def test_fm_broadcast_detects_few_stations(self):
        """FM 97.5 MHz recording should find 1-5 signals, not 25+."""
        samples, meta = _load_iq("fm_broadcast_97mhz")
        detector = _make_detector(meta)
        signals = detector.detect_from_iq(
            samples, center_freq=meta["center_freq_hz"], num_averages=8
        )
        assert 1 <= len(signals) <= 5, (
            f"Expected 1-5 FM stations, got {len(signals)}: "
            f"{[s['frequency_hz']/1e6 for s in signals]}"
        )

    def test_fm_broadcast_bandwidth_is_wide(self):
        """FM broadcast signals should merge into a detection wider than 10 kHz.

        The recording has a moderate-strength FM signal. With signal merging
        (merge_gap_bins), nearby detections should combine into a wider signal
        rather than many narrow spurs.
        """
        samples, meta = _load_iq("fm_broadcast_97mhz")
        # Use a larger merge gap to coalesce the FM signal's scattered peaks
        detector = _make_detector(meta, merge_gap_bins=50, min_signal_bins=1)
        signals = detector.detect_from_iq(
            samples, center_freq=meta["center_freq_hz"], num_averages=16
        )
        assert len(signals) >= 1, "Expected at least 1 FM station"
        strongest = signals[0]
        assert strongest["bandwidth_hz"] > 10_000, (
            f"Strongest FM signal bandwidth {strongest['bandwidth_hz']/1e3:.1f} kHz "
            f"is too narrow (expected > 10 kHz after merging)"
        )


class TestNoaaWeather:
    def test_noaa_finds_weather_channels(self):
        """NOAA 162 MHz recording should find signals in 162.4-162.55 MHz range."""
        samples, meta = _load_iq("noaa_weather_162mhz")
        detector = _make_detector(meta)
        signals = detector.detect_from_iq(
            samples, center_freq=meta["center_freq_hz"], num_averages=8
        )
        assert len(signals) >= 1, "Expected at least 1 NOAA weather signal"
        # At least one signal should be in the NOAA weather band
        noaa_signals = [
            s for s in signals
            if 162_400_000 <= s["frequency_hz"] <= 162_550_000
        ]
        assert len(noaa_signals) >= 1, (
            f"No signals found in NOAA range 162.4-162.55 MHz. "
            f"Detected: {[s['frequency_hz']/1e6 for s in signals]}"
        )


class TestNoiseFloor:
    def test_noise_floor_no_signals(self):
        """450 MHz noise recording should find 0 signals with reasonable threshold."""
        samples, meta = _load_iq("noise_floor_450mhz")
        detector = _make_detector(meta, snr_threshold_db=10.0)
        signals = detector.detect_from_iq(
            samples, center_freq=meta["center_freq_hz"], num_averages=8
        )
        assert len(signals) == 0, (
            f"Expected 0 signals in noise floor, got {len(signals)}: "
            f"{[(s['frequency_hz']/1e6, s['snr_db']) for s in signals]}"
        )
