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
