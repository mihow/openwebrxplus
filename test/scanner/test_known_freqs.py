"""Tests for the known frequency database."""

import pytest

from owrx.scanner.known_freqs import KNOWN_FREQS, match_known_freq


class TestMatchKnownFreq:
    """Tests for match_known_freq()."""

    def test_exact_noaa_match(self):
        assert match_known_freq(162_475_000) == "NOAA WX4 (Portland KIG77)"

    def test_all_noaa_channels(self):
        noaa = [
            (162_400_000, "NOAA WX1"),
            (162_425_000, "NOAA WX2"),
            (162_450_000, "NOAA WX3"),
            (162_475_000, "NOAA WX4 (Portland KIG77)"),
            (162_500_000, "NOAA WX5"),
            (162_525_000, "NOAA WX6"),
            (162_550_000, "NOAA WX7"),
        ]
        for freq, label in noaa:
            assert match_known_freq(freq) == label, f"Failed for {freq}"

    def test_within_tolerance(self):
        # 3 kHz off from NOAA WX4 — should still match with default 5 kHz tolerance
        result = match_known_freq(162_475_000 + 3000)
        assert result == "NOAA WX4 (Portland KIG77)"

    def test_at_tolerance_boundary(self):
        # Exactly at 5 kHz — should match (<=)
        result = match_known_freq(162_475_000 + 5000)
        assert result == "NOAA WX4 (Portland KIG77)"

    def test_beyond_tolerance(self):
        # 6 kHz off — should not match
        result = match_known_freq(162_475_000 + 6000)
        assert result is None

    def test_no_match(self):
        # Random frequency with nothing nearby
        assert match_known_freq(50_000_000) is None

    def test_custom_tolerance(self):
        # 8 kHz off, default tolerance would miss it, but 10 kHz catches it
        result = match_known_freq(162_475_000 + 8000, tolerance=10000)
        assert result == "NOAA WX4 (Portland KIG77)"

    def test_custom_tolerance_miss(self):
        # 3 kHz off but tolerance=1000 is too tight
        result = match_known_freq(162_475_000 + 3000, tolerance=1000)
        assert result is None

    def test_fm_broadcast_all_match(self):
        fm_calls = [
            "KBVM", "KMHD", "KQAC", "KBOO", "KOPB", "KGON", "KNRK", "KBFF",
            "KYCH", "KUPL", "KWJJ", "KKRZ", "KXL", "KINK", "KKCW", "KRSK",
            "KFBW", "KXJM",
        ]
        fm_freqs = [f for f in KNOWN_FREQS if 87_000_000 <= f <= 108_000_000]
        assert len(fm_freqs) == len(fm_calls), (
            f"Expected {len(fm_calls)} FM stations, got {len(fm_freqs)}"
        )
        for freq in fm_freqs:
            result = match_known_freq(freq)
            assert result is not None, f"No match for FM freq {freq/1e6:.1f} MHz"

    def test_air_band_emergency(self):
        assert match_known_freq(121_500_000) == "Air Emergency"

    def test_air_band_pdx_tower(self):
        assert match_known_freq(118_700_000) == "PDX Tower"

    def test_marine_ch16(self):
        assert match_known_freq(156_800_000) == "Marine Ch16 Distress"

    def test_marine_ch9(self):
        assert match_known_freq(156_450_000) == "Marine Ch9 Calling"

    def test_ham_2m_simplex(self):
        assert match_known_freq(146_520_000) == "2m National Simplex"

    def test_ham_70cm_simplex(self):
        assert match_known_freq(446_000_000) == "70cm National Simplex"

    def test_gmrs_ch1(self):
        assert match_known_freq(462_562_500) == "GMRS Ch 1"

    def test_gmrs_ch7(self):
        assert match_known_freq(462_712_500) == "GMRS Ch 7"

    def test_gmrs_all_channels(self):
        for ch in range(1, 8):
            freq = 462_562_500 + (ch - 1) * 25_000
            result = match_known_freq(freq)
            assert result == f"GMRS Ch {ch}", f"Failed for GMRS Ch {ch}"

    def test_float_frequency(self):
        # Frequencies may come in as floats from FFT calculations
        result = match_known_freq(162_475_000.0)
        assert result == "NOAA WX4 (Portland KIG77)"

    def test_closest_match_wins(self):
        # When two known freqs are within tolerance, closest should win.
        # NOAA WX4=162475000 and WX5=162500000 are 25 kHz apart.
        # With tolerance=15000, a freq at 162488000 is 13kHz from WX4 and 12kHz from WX5.
        result = match_known_freq(162_488_000, tolerance=15000)
        assert result == "NOAA WX5"
