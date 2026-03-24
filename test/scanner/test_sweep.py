import pytest

from owrx.scanner.sweep import FrequencySweeper, demod_mode_for_freq


class TestFrequencySweeper:
    """Sweeper configured for 100-110 MHz, 2.4 MHz sample rate, 0.8 usable BW ratio."""

    def make_sweeper(self, **kwargs):
        defaults = dict(
            freq_start=100_000_000,
            freq_stop=110_000_000,
            sample_rate=2_400_000,
            usable_bw_ratio=0.8,
        )
        defaults.update(kwargs)
        return FrequencySweeper(**defaults)

    def test_initial_window(self):
        s = self.make_sweeper()
        w = s.current_window()
        expected_center = 100_000_000 + 2_400_000 // 2
        assert w["center_freq"] == expected_center

    def test_advance_produces_next_window(self):
        s = self.make_sweeper()
        c1 = s.current_window()["center_freq"]
        s.advance()
        c2 = s.current_window()["center_freq"]
        assert c2 > c1

    def test_wraps_around_at_end(self):
        s = self.make_sweeper()
        for _ in range(s.total_windows):
            s.advance()
        # Should have wrapped back to the first window
        assert s.current_window()["center_freq"] == self.make_sweeper().current_window()["center_freq"]

    def test_total_windows(self):
        s = self.make_sweeper()
        # 10 MHz range / (2.4 MHz * 0.8) = 10 / 1.92 ≈ 5.2 → expect 5-7 windows
        assert 5 <= s.total_windows <= 7

    def test_skip_list(self):
        s_no_skip = self.make_sweeper()
        s_skip = self.make_sweeper(skip_ranges=[(103_000_000, 106_500_000)])
        assert s_skip.total_windows < s_no_skip.total_windows
        # No window should be entirely inside 103-105 MHz
        for _ in range(s_skip.total_windows):
            w = s_skip.current_window()
            low = w["low_freq"]
            high = w["high_freq"]
            entirely_inside = low >= 103_000_000 and high <= 106_500_000
            assert not entirely_inside, f"Window {low}-{high} is entirely inside skip range"
            s_skip.advance()

    def test_progress_fraction(self):
        s = self.make_sweeper()
        assert s.progress == pytest.approx(0.0, abs=0.01)
        # Advance halfway
        half = s.total_windows // 2
        for _ in range(half):
            s.advance()
        assert s.progress == pytest.approx(half / s.total_windows, abs=0.1)

    def test_demod_mode_for_frequency(self):
        assert demod_mode_for_freq(91_500_000) == "wfm"
        assert demod_mode_for_freq(121_500_000) == "am"
        assert demod_mode_for_freq(162_475_000) == "nfm"
        assert demod_mode_for_freq(446_000_000) == "nfm"

    def test_current_window_has_expected_keys(self):
        s = self.make_sweeper()
        w = s.current_window()
        assert "center_freq" in w
        assert "sample_rate" in w
        assert "low_freq" in w
        assert "high_freq" in w
        assert "demod_mode" in w

    def test_reset(self):
        s = self.make_sweeper()
        first = s.current_window()["center_freq"]
        s.advance()
        s.advance()
        s.reset()
        assert s.current_window()["center_freq"] == first
