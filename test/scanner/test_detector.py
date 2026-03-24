import numpy as np
import pytest

from owrx.scanner.detector import SignalDetector


@pytest.fixture
def detector():
    return SignalDetector(fft_size=1024, sample_rate=2_400_000, snr_threshold_db=10.0)


def _flat_noise(fft_size=1024, noise_db=-90.0):
    """Create a flat noise floor at the given dB level."""
    rng = np.random.default_rng(42)
    return noise_db + rng.normal(0, 0.5, fft_size)


def _inject_peak(fft, center_bin, width_bins, peak_db):
    """Inject a gaussian-ish peak into an FFT array."""
    fft = fft.copy()
    half = width_bins // 2
    lo = max(0, center_bin - half)
    hi = min(len(fft), center_bin + half)
    for b in range(lo, hi):
        fft[b] = peak_db
    return fft


class TestSignalDetector:
    def test_no_signals_in_noise(self, detector):
        fft = _flat_noise()
        signals = detector.detect(fft, center_freq=100e6)
        assert signals == []

    def test_single_strong_signal(self, detector):
        fft = _flat_noise()
        fft = _inject_peak(fft, center_bin=512, width_bins=10, peak_db=-70.0)
        signals = detector.detect(fft, center_freq=100e6)
        assert len(signals) == 1
        # Bin 512 = center_freq for 1024-bin FFT
        assert abs(signals[0]["frequency_hz"] - 100e6) < 50_000
        assert signals[0]["snr_db"] >= 10.0

    def test_multiple_signals(self, detector):
        fft = _flat_noise()
        fft = _inject_peak(fft, center_bin=200, width_bins=10, peak_db=-65.0)
        fft = _inject_peak(fft, center_bin=800, width_bins=10, peak_db=-70.0)
        signals = detector.detect(fft, center_freq=100e6)
        assert len(signals) == 2
        # Sorted by peak power descending
        assert signals[0]["peak_power_db"] >= signals[1]["peak_power_db"]

    def test_weak_signal_below_threshold(self, detector):
        fft = _flat_noise()
        # Only 5 dB above noise (-90), threshold is 10 dB
        fft = _inject_peak(fft, center_bin=512, width_bins=10, peak_db=-85.0)
        signals = detector.detect(fft, center_freq=100e6)
        assert signals == []

    def test_noise_floor_tracking(self, detector):
        fft = _flat_noise(noise_db=-90.0)
        detector.detect(fft, center_freq=100e6)
        assert detector.noise_floor_db is not None
        assert abs(detector.noise_floor_db - (-90.0)) < 2.0

    def test_signal_bandwidth_estimation(self, detector):
        fft = _flat_noise()
        # 24-bin-wide peak; bin_width = 2.4 MHz / 1024 ~ 2343 Hz
        # 24 bins ~ 56 kHz
        fft = _inject_peak(fft, center_bin=512, width_bins=24, peak_db=-65.0)
        signals = detector.detect(fft, center_freq=100e6)
        assert len(signals) == 1
        assert signals[0]["bandwidth_hz"] > 40_000

    def test_bin_to_frequency_conversion(self, detector):
        # Bin 0 should map to center_freq - sample_rate/2
        freq = detector._bin_to_freq(0, center_freq=100e6)
        expected = 100e6 - 2_400_000 / 2
        assert freq == expected
