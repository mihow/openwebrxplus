"""Tests for the classification pipeline."""

from owrx.scanner.classifier import (
    AnyFilter,
    ClassificationPipeline,
    ContentFilter,
    VoiceFilter,
    estimate_mode_from_bandwidth,
)


class RejectAllFilter(ContentFilter):
    def check(self, signal_info: dict) -> str:
        return "rejected"


class TestClassificationPipeline:
    def test_classify_returns_result(self):
        pipeline = ClassificationPipeline()
        result = pipeline.classify(
            frequency_hz=91_500_000,
            bandwidth_hz=180_000,
            peak_power_db=-30.0,
            snr_db=20.0,
        )
        assert "mode" in result
        assert "classification" in result
        assert "filter_result" in result
        assert "action" in result

    def test_auto_mode_detection(self):
        pipeline = ClassificationPipeline()
        result = pipeline.classify(
            frequency_hz=91_500_000,
            bandwidth_hz=180_000,
            peak_power_db=-30.0,
            snr_db=20.0,
        )
        assert result["mode"] == "wfm"

    def test_any_filter_passes_everything(self):
        pipeline = ClassificationPipeline(content_filter=AnyFilter())
        result = pipeline.classify(
            frequency_hz=91_500_000,
            bandwidth_hz=180_000,
            peak_power_db=-30.0,
            snr_db=20.0,
        )
        assert result["action"] == "unsquelch"

    def test_voice_filter_placeholder(self):
        pipeline = ClassificationPipeline(content_filter=VoiceFilter())
        result = pipeline.classify(
            frequency_hz=91_500_000,
            bandwidth_hz=180_000,
            peak_power_db=-30.0,
            snr_db=20.0,
        )
        assert result["action"] == "unsquelch"

    def test_custom_filter(self):
        pipeline = ClassificationPipeline(content_filter=RejectAllFilter())
        result = pipeline.classify(
            frequency_hz=91_500_000,
            bandwidth_hz=180_000,
            peak_power_db=-30.0,
            snr_db=20.0,
        )
        assert result["action"] == "log-only"

    def test_bandwidth_suggests_wfm(self):
        assert estimate_mode_from_bandwidth(180_000) == "wfm"

    def test_bandwidth_suggests_nfm(self):
        assert estimate_mode_from_bandwidth(12_500) == "nfm"

    def test_nfm_repeater_not_downgraded_to_am(self):
        """443 MHz NFM repeater with narrow detected BW should stay NFM."""
        pipeline = ClassificationPipeline()
        result = pipeline.classify(
            frequency_hz=443_150_000,
            bandwidth_hz=2_900,
            peak_power_db=-40.0,
            snr_db=15.0,
        )
        assert result["mode"] == "nfm"

    def test_fm_broadcast_not_downgraded_to_nfm(self):
        """97 MHz FM broadcast with 64.5 kHz BW should be WFM."""
        pipeline = ClassificationPipeline()
        result = pipeline.classify(
            frequency_hz=97_000_000,
            bandwidth_hz=64_500,
            peak_power_db=-30.0,
            snr_db=20.0,
        )
        assert result["mode"] == "wfm"

    def test_band_mode_authoritative_over_bandwidth(self):
        """Frequency band should be authoritative; narrow BW should not override."""
        pipeline = ClassificationPipeline()
        # VHF marine freq (156 MHz) with narrow BW — should stay NFM
        result = pipeline.classify(
            frequency_hz=156_800_000,
            bandwidth_hz=3_000,
            peak_power_db=-35.0,
            snr_db=12.0,
        )
        assert result["mode"] == "nfm"
