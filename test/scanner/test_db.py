import os
import tempfile
import time

import pytest

from owrx.scanner.db import ScannerDatabase


@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = ScannerDatabase(path)
    yield database
    database.close()
    os.unlink(path)


class TestScannerDatabase:
    def test_creates_tables_on_init(self, db):
        tables = db.list_tables()
        assert "detections" in tables
        assert "bookmarks" in tables
        assert "scan_sessions" in tables

    def test_log_detection(self, db):
        det_id = db.log_detection(
            frequency_hz=162550000,
            mode="NFM",
            peak_power_db=-42.5,
            snr_db=18.3,
            classification="weather",
            bookmark_label="NOAA Weather",
        )
        assert det_id is not None
        det = db.get_detection(det_id)
        assert det["frequency_hz"] == 162550000
        assert det["mode"] == "NFM"
        assert det["peak_power_db"] == -42.5
        assert det["snr_db"] == 18.3
        assert det["classification"] == "weather"
        assert det["bookmark_label"] == "NOAA Weather"
        assert det["timestamp"] is not None

    def test_update_detection_duration(self, db):
        det_id = db.log_detection(frequency_hz=462562500, mode="NFM", peak_power_db=-50.0)
        db.update_detection(det_id, duration_sec=12.5, recording_path="/tmp/rec_001.wav")
        det = db.get_detection(det_id)
        assert det["duration_sec"] == 12.5
        assert det["recording_path"] == "/tmp/rec_001.wav"

    def test_get_recent_detections(self, db):
        for i in range(5):
            db.log_detection(frequency_hz=100000000 + i * 1000, mode="NFM", peak_power_db=-40.0)
        recent = db.get_recent_detections(limit=3)
        assert len(recent) == 3
        # Most recent first (highest frequency was inserted last)
        assert recent[0]["frequency_hz"] > recent[2]["frequency_hz"]

    def test_get_most_active_frequencies(self, db):
        # Log several detections on the same frequency
        for _ in range(5):
            db.log_detection(frequency_hz=462562500, mode="NFM", peak_power_db=-45.0)
        for _ in range(2):
            db.log_detection(frequency_hz=162550000, mode="NFM", peak_power_db=-50.0)
        db.log_detection(frequency_hz=155000000, mode="NFM", peak_power_db=-60.0)

        active = db.get_most_active(hours=24, limit=10)
        assert len(active) == 3
        assert active[0]["frequency_hz"] == 462562500
        assert active[0]["count"] == 5
        assert active[1]["frequency_hz"] == 162550000
        assert active[1]["count"] == 2

    def test_add_bookmark(self, db):
        bm_id = db.add_bookmark(frequency_hz=162550000, label="NOAA Weather", mode="NFM")
        assert bm_id is not None
        bm = db.get_bookmark(bm_id)
        assert bm["frequency_hz"] == 162550000
        assert bm["label"] == "NOAA Weather"
        assert bm["mode"] == "NFM"
        assert bm["created_at"] is not None

        all_bm = db.get_all_bookmarks()
        assert len(all_bm) == 1

    def test_start_and_stop_scan_session(self, db):
        config = {"range_hz": [400000000, 470000000], "step_hz": 12500}
        session_id = db.start_session(config)
        assert session_id is not None

        session = db.get_session(session_id)
        assert session["started_at"] is not None
        assert session["stopped_at"] is None
        assert '"range_hz"' in session["config_json"]

        db.stop_session(session_id)
        session = db.get_session(session_id)
        assert session["stopped_at"] is not None

    def test_clear_recording_path(self, db):
        det_id = db.log_detection(frequency_hz=462562500, mode="NFM", peak_power_db=-50.0)
        db.update_detection(det_id, recording_path="/tmp/rec_002.wav")
        det = db.get_detection(det_id)
        assert det["recording_path"] == "/tmp/rec_002.wav"

        db.clear_recording_path(det_id)
        det = db.get_detection(det_id)
        assert det["recording_path"] is None
