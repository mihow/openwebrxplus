"""Tests for owrx.scanner.recorder.ScannerRecorder."""

import os
import time
from pathlib import Path

import numpy as np
import pytest

from owrx.scanner.recorder import ScannerRecorder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_recorder(tmp_path, **kwargs) -> ScannerRecorder:
    defaults = dict(
        storage_path=str(tmp_path),
        sample_rate=8_000,
        quality_kbps=24,
        max_storage_mb=100,
        retention_days=30,
        max_clip_sec=300,
    )
    defaults.update(kwargs)
    return ScannerRecorder(**defaults)


def _sine_samples(sample_rate: int = 8_000, duration_sec: float = 0.5) -> np.ndarray:
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    return np.sin(2 * np.pi * 440 * t).astype(np.float32)


def _wait_for_file(path: str, timeout: float = 5.0):
    """Block until path exists and has non-zero size, or raise."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        p = Path(path)
        if p.exists() and p.stat().st_size > 0:
            return
        time.sleep(0.05)
    raise TimeoutError(f"File never appeared / remained empty: {path}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRecordingCreatesFile:
    def test_recording_creates_file(self, tmp_path):
        rec = _make_recorder(tmp_path)
        path = rec.start_recording(frequency_hz=146_520_000, mode="nfm")
        rec.write_audio(_sine_samples())
        final_path = rec.stop_recording()

        assert final_path == path
        _wait_for_file(final_path)
        assert Path(final_path).stat().st_size > 0


class TestRecordingPathFormat:
    def test_path_contains_date_directory(self, tmp_path):
        from datetime import datetime
        rec = _make_recorder(tmp_path)
        path = rec.start_recording(frequency_hz=146_520_000, mode="nfm")
        rec.stop_recording()

        p = Path(path)
        date_dir = p.parent.name
        # Must match YYYY-MM-DD
        assert len(date_dir) == 10
        parts = date_dir.split("-")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_filename_contains_freq_and_mode(self, tmp_path):
        rec = _make_recorder(tmp_path)
        path = rec.start_recording(frequency_hz=162_400_000, mode="NFM")
        rec.stop_recording()

        filename = Path(path).name
        assert "162400000" in filename
        assert "nfm" in filename.lower()

    def test_path_under_recordings_subdir(self, tmp_path):
        rec = _make_recorder(tmp_path)
        path = rec.start_recording(frequency_hz=100_000_000, mode="wfm")
        rec.stop_recording()

        p = Path(path)
        # recordings/{YYYY-MM-DD}/filename
        assert p.parts[-3] == "recordings"

    def test_extension_is_ogg_or_wav(self, tmp_path):
        rec = _make_recorder(tmp_path)
        path = rec.start_recording(frequency_hz=100_000_000, mode="am")
        rec.stop_recording()

        assert Path(path).suffix in (".ogg", ".wav")


class TestMaxClipDuration:
    def test_auto_stop_after_max_clip_sec(self, tmp_path):
        rec = _make_recorder(tmp_path, max_clip_sec=1, sample_rate=8_000)
        path = rec.start_recording(frequency_hz=146_520_000, mode="nfm")

        # Write a tiny bit, then wait past the limit
        rec.write_audio(_sine_samples(sample_rate=8_000, duration_sec=0.1))
        time.sleep(1.1)

        # Next write should hit the time guard and auto-stop
        rec.write_audio(_sine_samples(sample_rate=8_000, duration_sec=0.1))

        # Recorder should no longer be active
        assert rec._current_path is None
        assert rec._proc is None

        _wait_for_file(path)

    def test_recording_still_active_before_limit(self, tmp_path):
        rec = _make_recorder(tmp_path, max_clip_sec=60)
        rec.start_recording(frequency_hz=146_520_000, mode="nfm")
        rec.write_audio(_sine_samples())

        # Should still be active
        assert rec._current_path is not None
        rec.stop_recording()


class TestPruneOldRecordings:
    def _make_old_file(self, recordings_root: Path, days_old: int) -> Path:
        date_dir = recordings_root / "2000-01-01"
        date_dir.mkdir(parents=True, exist_ok=True)
        f = date_dir / f"old_{days_old}d.ogg"
        f.write_bytes(b"\x00" * 1024)
        # Set mtime to `days_old` days in the past
        old_mtime = time.time() - days_old * 86_400
        os.utime(f, (old_mtime, old_mtime))
        return f

    def test_old_files_deleted(self, tmp_path):
        rec = _make_recorder(tmp_path, retention_days=7)
        recordings_root = tmp_path / "recordings"
        old_file = self._make_old_file(recordings_root, days_old=30)

        rec.prune_old_recordings()

        assert not old_file.exists()

    def test_recent_files_kept(self, tmp_path):
        rec = _make_recorder(tmp_path, retention_days=30)
        recordings_root = tmp_path / "recordings"
        recent = recordings_root / "2099-01-01"
        recent.mkdir(parents=True, exist_ok=True)
        f = recent / "recent.ogg"
        f.write_bytes(b"\x00" * 512)

        rec.prune_old_recordings()

        assert f.exists()

    def test_prune_enforces_storage_cap(self, tmp_path):
        # max_storage_mb = 1 MiB; create 3 × 512 KiB files (= 1.5 MiB)
        rec = _make_recorder(tmp_path, retention_days=365, max_storage_mb=1)
        recordings_root = tmp_path / "recordings"
        date_dir = recordings_root / "2099-06-01"
        date_dir.mkdir(parents=True, exist_ok=True)

        block = b"\x00" * (512 * 1024)
        files = []
        base_mtime = time.time() - 3600
        for i in range(3):
            f = date_dir / f"clip_{i:02d}.ogg"
            f.write_bytes(block)
            mtime = base_mtime + i  # i=0 is oldest
            os.utime(f, (mtime, mtime))
            files.append(f)

        rec.prune_old_recordings()

        # Total should now be ≤ 1 MiB
        assert rec.get_storage_usage_mb() <= 1.0


class TestStorageUsage:
    def test_empty_storage_is_zero(self, tmp_path):
        rec = _make_recorder(tmp_path)
        assert rec.get_storage_usage_mb() == pytest.approx(0.0)

    def test_tracks_size_after_files_written(self, tmp_path):
        rec = _make_recorder(tmp_path)
        recordings_root = tmp_path / "recordings" / "2099-01-01"
        recordings_root.mkdir(parents=True, exist_ok=True)

        size_bytes = 256 * 1024  # 256 KiB
        f = recordings_root / "clip.ogg"
        f.write_bytes(b"\x00" * size_bytes)

        usage = rec.get_storage_usage_mb()
        assert usage == pytest.approx(size_bytes / (1024 * 1024), rel=1e-3)

    def test_tracks_multiple_files(self, tmp_path):
        rec = _make_recorder(tmp_path)
        recordings_root = tmp_path / "recordings" / "2099-01-01"
        recordings_root.mkdir(parents=True, exist_ok=True)

        for i in range(4):
            f = recordings_root / f"clip_{i}.ogg"
            f.write_bytes(b"\x00" * 1024)

        assert rec.get_storage_usage_mb() == pytest.approx(4 * 1024 / (1024 * 1024), rel=1e-3)


class TestStopWithoutStart:
    def test_stop_without_start_no_error(self, tmp_path):
        rec = _make_recorder(tmp_path)
        result = rec.stop_recording()
        assert result == ""

    def test_write_without_start_no_error(self, tmp_path):
        rec = _make_recorder(tmp_path)
        # Should not raise
        rec.write_audio(_sine_samples())

    def test_double_stop_no_error(self, tmp_path):
        rec = _make_recorder(tmp_path)
        rec.start_recording(frequency_hz=146_000_000, mode="nfm")
        rec.write_audio(_sine_samples())
        rec.stop_recording()
        result = rec.stop_recording()  # second stop
        assert result == ""
