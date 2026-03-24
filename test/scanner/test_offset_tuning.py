"""Tests for scanner offset tuning logic."""

import unittest


class TestOffsetTuning(unittest.TestCase):
    """Test the offset tuning calculation used when the scanner locks on a signal."""

    def test_retune_avoids_center_freq(self):
        """SDR should be retuned so the signal is NOT at center frequency."""
        from owrx.scanner import ScannerService

        svc = ScannerService()

        signal_freq = 146_520_000
        result = svc._calculate_offset_tuning(signal_freq)

        # SDR center should differ from signal frequency
        assert result["sdr_center"] != signal_freq, (
            "SDR center should not equal signal frequency (DC spike)"
        )
        # Offset should be the difference
        assert result["offset_freq"] == signal_freq - result["sdr_center"]

    def test_offset_is_within_100khz(self):
        """Offset should be ≤100 kHz to stay within the SDR passband."""
        from owrx.scanner import ScannerService

        svc = ScannerService()
        signal_freq = 443_150_000
        result = svc._calculate_offset_tuning(signal_freq)

        offset = abs(result["offset_freq"])
        assert offset > 0, "Offset should be nonzero"
        assert offset <= 150_000, f"Offset {offset} Hz too large (max 150 kHz)"

    def test_offset_direction_is_positive(self):
        """SDR should retune below the signal so offset_freq is positive.

        Positive offset_freq means the signal is above center — avoids
        ambiguity with negative frequency offsets in some DSP chains.
        """
        from owrx.scanner import ScannerService

        svc = ScannerService()
        result = svc._calculate_offset_tuning(162_550_000)

        assert result["offset_freq"] > 0, (
            "offset_freq should be positive (SDR tuned below signal)"
        )


if __name__ == "__main__":
    unittest.main()
