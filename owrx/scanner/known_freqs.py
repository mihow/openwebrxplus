"""Known frequency database for signal labeling.

Provides match_known_freq() to look up a human-readable label for a detected
frequency. Currently covers the Portland, OR metro area.
"""

# Each entry: frequency in Hz -> label string
KNOWN_FREQS: dict[int, str] = {}


def _add(freq_hz: int, label: str) -> None:
    KNOWN_FREQS[freq_hz] = label


# --- NOAA Weather Radio (nationally standardized) ---
_add(162_400_000, "NOAA WX1")
_add(162_425_000, "NOAA WX2")
_add(162_450_000, "NOAA WX3")
_add(162_475_000, "NOAA WX4 (Portland KIG77)")
_add(162_500_000, "NOAA WX5")
_add(162_525_000, "NOAA WX6")
_add(162_550_000, "NOAA WX7")

# --- Portland FM Broadcast ---
_add(88_300_000, "KBVM Religious")
_add(89_100_000, "KMHD Jazz")
_add(89_900_000, "KQAC Classical")
_add(90_700_000, "KBOO Community")
_add(91_500_000, "KOPB OPB/NPR")
_add(92_300_000, "KGON Classic Rock")
_add(94_700_000, "KNRK Alternative")
_add(95_500_000, "KBFF Top 40")
_add(97_100_000, "KYCH Variety")
_add(98_700_000, "KUPL Country")
_add(99_500_000, "KWJJ Country")
_add(100_300_000, "KKRZ Top 40")
_add(101_100_000, "KXL News")
_add(101_900_000, "KINK Indie")
_add(103_300_000, "KKCW K103")
_add(105_100_000, "KRSK Sports")
_add(105_900_000, "KFBW Classic Rock")
_add(107_500_000, "KXJM Hip-Hop")

# --- Air Band (Portland) ---
_add(121_500_000, "Air Emergency")
_add(118_700_000, "PDX Tower")
_add(124_350_000, "Portland Approach")
_add(128_350_000, "PDX Ground")
_add(132_950_000, "Portland Departure")

# --- Marine VHF ---
_add(156_800_000, "Marine Ch16 Distress")
_add(156_450_000, "Marine Ch9 Calling")
_add(156_650_000, "Marine Ch13 Bridge-Bridge")

# --- Ham simplex ---
_add(146_520_000, "2m National Simplex")
_add(446_000_000, "70cm National Simplex")

# --- Portland repeaters (from prior scans) ---
_add(443_150_000, "Mount Scott Repeater?")
_add(440_400_000, "W7RAT KOIN Tower")
_add(442_225_000, "K7RPT KOIN Tower")

# --- GMRS channels 1-7 (462.5625 - 462.7250 MHz, 25 kHz spacing) ---
for _ch in range(1, 8):
    _freq = 462_562_500 + (_ch - 1) * 25_000
    _add(_freq, f"GMRS Ch {_ch}")

# Clean up module namespace
del _ch, _freq


def match_known_freq(freq_hz: int | float, tolerance: int = 5000) -> str | None:
    """Match a frequency to a known label.

    Args:
        freq_hz: Frequency in Hz to look up.
        tolerance: Maximum distance in Hz for a match (default 5 kHz).

    Returns:
        Label string if matched, None otherwise.
    """
    best_label = None
    best_dist = tolerance + 1
    for known_freq, label in KNOWN_FREQS.items():
        dist = abs(freq_hz - known_freq)
        if dist < best_dist:
            best_dist = dist
            best_label = label
    if best_dist <= tolerance:
        return best_label
    return None
