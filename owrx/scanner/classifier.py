"""Classification pipeline — mode detection, content filtering, and action routing.

Processes detected signals through pluggable stages:
  1. Mode auto-detect (band plan + bandwidth refinement)
  2. Classification (analog/digital/unknown)
  3. Content filter (pluggable: voice detection, etc.)
  4. Action decision (unsquelch / log-only)
"""

from owrx.scanner.sweep import demod_mode_for_freq

ANALOG_MODES = {"wfm", "nfm", "am"}


def estimate_mode_from_bandwidth(bandwidth_hz: float) -> str:
    """Suggest a demod mode based on signal bandwidth."""
    if bandwidth_hz > 100_000:
        return "wfm"
    elif bandwidth_hz > 5_000:
        return "nfm"
    return "am"


class ContentFilter:
    """Base class for content filters. Subclass and override check()."""

    def check(self, signal_info: dict) -> str:
        """Return 'passed', 'rejected', or 'log-only'."""
        return "passed"


class AnyFilter(ContentFilter):
    """Passes everything."""

    def check(self, signal_info: dict) -> str:
        return "passed"


class VoiceFilter(ContentFilter):
    """Placeholder for voice-activity detection. Passes everything for now."""

    def check(self, signal_info: dict) -> str:
        return "passed"


class ClassificationPipeline:
    """Runs a signal through mode detection, classification, filtering, and action."""

    def __init__(self, content_filter: ContentFilter | None = None):
        self._filter = content_filter or AnyFilter()

    def classify(
        self,
        frequency_hz: int,
        bandwidth_hz: float,
        peak_power_db: float,
        snr_db: float,
        audio_buffer: bytes | None = None,
    ) -> dict:
        # Stage 1: Mode auto-detect — frequency band is authoritative
        mode = demod_mode_for_freq(frequency_hz)

        # Only upgrade to WFM if bandwidth evidence is strong
        # (detected BW > 40 kHz suggests broadcast FM)
        if bandwidth_hz and bandwidth_hz > 40000 and mode != "am":
            mode = "wfm"

        # Stage 2: classification
        classification = "analog" if mode in ANALOG_MODES else "unknown"

        # Stage 3: content filter
        signal_info = {
            "frequency_hz": frequency_hz,
            "bandwidth_hz": bandwidth_hz,
            "peak_power_db": peak_power_db,
            "snr_db": snr_db,
            "mode": mode,
            "classification": classification,
            "audio_buffer": audio_buffer,
        }
        filter_result = self._filter.check(signal_info)

        # Stage 4: action
        action = "unsquelch" if filter_result == "passed" else "log-only"

        return {
            "mode": mode,
            "classification": classification,
            "filter_result": filter_result,
            "action": action,
        }
