"""Frequency sweeper — scan window management and retune logic.

Manages which frequency window to tune to next as the scanner sweeps
across a range. Pure logic — no SDR interaction.
"""

# (low_hz, high_hz, mode)
BAND_MODES: list[tuple[int, int, str]] = [
    (25_000_000, 30_000_000, "am"),
    (30_000_000, 88_000_000, "nfm"),
    (88_000_000, 108_000_000, "wfm"),
    (108_000_000, 137_000_000, "am"),
    (137_000_000, 174_000_000, "nfm"),
    (174_000_000, 400_000_000, "nfm"),
    (400_000_000, 470_000_000, "nfm"),
    (470_000_000, 960_000_000, "nfm"),
    (960_000_000, 1_700_000_000, "am"),
]


def demod_mode_for_freq(freq_hz: int) -> str:
    """Return the default demodulation mode for a given frequency."""
    for low, high, mode in BAND_MODES:
        if low <= freq_hz < high:
            return mode
    return "nfm"  # fallback


class FrequencySweeper:
    """Manages scan windows across a frequency range.

    Builds a list of window center frequencies spaced by
    sample_rate * usable_bw_ratio, skipping windows that fall
    entirely inside any skip range.
    """

    def __init__(
        self,
        freq_start: int,
        freq_stop: int,
        sample_rate: int,
        usable_bw_ratio: float = 0.8,
        skip_ranges: list[tuple[int, int]] | None = None,
    ):
        self._sample_rate = sample_rate
        self._usable_bw_ratio = usable_bw_ratio
        self._skip_ranges = skip_ranges or []
        self._index = 0

        step = int(sample_rate * usable_bw_ratio)
        half_sr = sample_rate // 2

        # Build window centers
        centers: list[int] = []
        center = freq_start + half_sr
        while center - half_sr < freq_stop:
            centers.append(center)
            center += step

        # Filter out windows entirely inside a skip range
        self._centers: list[int] = []
        for c in centers:
            low = c - half_sr
            high = c + half_sr
            if not self._is_skipped(low, high):
                self._centers.append(c)

    def _is_skipped(self, low: int, high: int) -> bool:
        """Return True if the window [low, high] is entirely inside any skip range."""
        for skip_low, skip_high in self._skip_ranges:
            if low >= skip_low and high <= skip_high:
                return True
        return False

    @property
    def total_windows(self) -> int:
        return len(self._centers)

    @property
    def progress(self) -> float:
        if self.total_windows == 0:
            return 0.0
        return self._index / self.total_windows

    def current_window(self) -> dict:
        center = self._centers[self._index]
        half_sr = self._sample_rate // 2
        return {
            "center_freq": center,
            "sample_rate": self._sample_rate,
            "low_freq": center - half_sr,
            "high_freq": center + half_sr,
            "demod_mode": demod_mode_for_freq(center),
        }

    def advance(self) -> None:
        self._index = (self._index + 1) % self.total_windows

    def reset(self) -> None:
        self._index = 0
