"""Known frequency database for signal labeling.

Provides match_known_freq() to look up a human-readable label for a detected
frequency. Currently covers the Portland, OR metro area.
Sources: RepeaterBook, ARRG, PARC, RadioReference, NWS Portland.
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
_add(162_525_000, "NOAA WX6 (WNG604 Woodland)")
_add(162_550_000, "NOAA WX7 (KIG98 Portland)")

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
_add(118_700_000, "PDX Tower")
_add(121_500_000, "Air Emergency")
_add(124_350_000, "Portland Approach")
_add(128_350_000, "PDX Ground")
_add(132_950_000, "Portland Departure")

# --- Marine VHF (Columbia/Willamette) ---
_add(156_450_000, "Marine Ch9 Calling")
_add(156_650_000, "Marine Ch13 Bridge-Bridge")
_add(156_800_000, "Marine Ch16 Distress")
_add(157_100_000, "Marine Ch22A Coast Guard")

# --- 2m Repeaters: Portland / Multnomah County ---
_add(145_230_000, "K7LJ 145.230 Council Crest")
_add(145_310_000, "AB7BS 145.310 Skyline")
_add(145_390_000, "K7LJ 145.390 Mt Tabor")
_add(146_700_000, "KE7AWR 146.700 Stonehenge (Fusion)")
_add(146_840_000, "W7LT 146.840 Larch Mtn (PARC)")
_add(146_980_000, "AB7BS 146.980 KGW Tower")
_add(147_040_000, "K7RPT 147.040 Sylvan (ARRG)")
_add(147_140_000, "W7AC 147.140 Skyline")

# --- 2m Repeaters: WORC Linked Network ---
_add(145_270_000, "WORC 145.270 linked")
_add(145_430_000, "WORC 145.430 Colton")
_add(146_800_000, "WORC 146.800 linked")

# --- 2m Repeaters: ARRG / wider metro ---
_add(146_960_000, "OTVARC 146.960")
_add(147_120_000, "147.120 Mt Hood area")
_add(147_280_000, "HARC 147.280 Hoodview")
_add(147_320_000, "K7RPT 147.320 (ARRG)")
_add(147_360_000, "147.360 Cooper Mtn (ARES)")

# --- 2m Repeaters: Vancouver WA ---
_add(146_730_000, "KB7APU 146.730 DMR Vancouver")

# --- 2m Simplex ---
_add(146_520_000, "2m National Simplex")
_add(146_580_000, "2m Regional Simplex")

# --- 70cm Repeaters: Portland / Multnomah County ---
_add(440_350_000, "N7QQU 440.350 Stonehenge")
_add(440_400_000, "W7RAT 440.400 KOIN Tower")
_add(440_450_000, "N7PIR 440.450 Skyline")
_add(440_475_000, "K0HSU 440.475 OHSU")
_add(440_500_000, "AB7BS 440.500 KGW Tower")
_add(440_512_500, "K7RPT 440.5125 DMR KOIN Tower")
_add(440_625_000, "KB7APU 440.625 DMR W Hills")
_add(440_825_000, "K7LHS 440.825 Emanuel Hospital")
_add(441_350_000, "AB7BS 441.350 Skyline")
_add(442_225_000, "K7RPT 442.225 KOIN Tower")
_add(442_650_000, "K7LJ 442.650 Council Crest")
_add(442_700_000, "K7LTA 442.700 OHSU")
_add(443_050_000, "WA7BND 443.050 Stonehenge")
_add(443_200_000, "W7PRN 443.200 Skyline")
_add(443_225_000, "W7PMC 443.225 Portland")
_add(443_275_000, "KA7AGH 443.275 Healy Heights")
_add(443_300_000, "K7LJ 443.300 Council Crest")
_add(443_625_000, "W7DTV 443.625 Skyline")
_add(444_675_000, "W7PGE 444.675 Council Crest")
_add(444_800_000, "N7PRM 444.800 Portland")
_add(444_837_500, "WA7HAA 444.8375 DMR Providence")

# --- 70cm Repeaters: WORC Linked Network ---
_add(443_150_000, "WORC 443.150 linked")
_add(442_525_000, "WORC 442.525 linked")

# --- 70cm Repeaters: ARRG / K7RPT ---
_add(442_325_000, "K7RPT 442.325 (ARRG linked)")
_add(444_400_000, "K7RPT 444.400 (ARRG linked)")

# --- 70cm Repeaters: wider metro ---
_add(440_075_000, "K0HSU 440.075 Hillsboro")
_add(440_575_000, "WA7LO 440.575 Lake Oswego")
_add(442_075_000, "W7ZRS 442.075 Oregon City")
_add(444_300_000, "444.300 Lake Oswego")
_add(444_750_000, "W7BVT 444.750 Beaverton")
_add(444_850_000, "W7PSV 444.850 St Vincent")
_add(444_975_000, "K7CPU 444.975 Hillsboro")

# --- 70cm Repeaters: Vancouver WA ---
_add(442_100_000, "K7GJT 442.100 Vancouver")
_add(443_675_000, "KE7FUW 443.675 Larch Mtn")
_add(443_825_000, "W7AIA 443.825 Vancouver")
_add(443_975_000, "KB7APU 443.975 Vancouver")
_add(444_550_000, "N7XMT 444.550 Vancouver")

# --- 70cm Repeaters: Gresham / East Metro ---
_add(441_625_000, "KE7AWR 441.625 Walters Hill Gresham")
_add(443_250_000, "N7KOJ 443.250 Gresham")

# --- 70cm Simplex ---
_add(446_000_000, "70cm National Simplex")

# --- 1.25m Band ---
_add(224_340_000, "K7JCN 224.340 Oregon City")
_add(224_640_000, "AB7F 224.640 Vancouver WA")

# --- Railroad (Portland metro) ---
_add(160_515_000, "UP Railroad E Portland")
_add(160_680_000, "UP Albina Yard")
_add(160_650_000, "BNSF Willbridge Yard")
_add(161_250_000, "BNSF Portland-Washougal")
_add(161_415_000, "BNSF Washougal-SPS Jct")

# --- GMRS channels 1-7 (462.5625 - 462.7250 MHz, 25 kHz spacing) ---
for _ch in range(1, 8):
    _freq = 462_562_500 + (_ch - 1) * 25_000
    _add(_freq, f"GMRS Ch {_ch}")

# --- GMRS Repeaters (Portland metro, open) ---
_add(462_650_000, "GMRS Rpt Cooper Mtn Beaverton")
_add(462_700_000, "GMRS Rpt Goat Mtn Colton")
_add(462_600_000, "GMRS Rpt Lake Oswego")
_add(462_725_000, "GMRS Rpt Forest Grove")

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
