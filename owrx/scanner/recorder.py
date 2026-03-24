"""Audio recorder for the scanner.

Encodes Float32 PCM audio samples to Opus/OGG via an ffmpeg subprocess.
Falls back to WAV if ffmpeg is unavailable.

File layout:
    {storage_path}/recordings/{YYYY-MM-DD}/{timestamp}_{freq_hz}_{mode}.ogg
"""

import logging
import os
import shutil
import struct
import subprocess
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


class ScannerRecorder:
    """Record demodulated audio for a single active signal at a time.

    Parameters
    ----------
    storage_path:
        Root directory for recordings.  Sub-directories are created automatically.
    sample_rate:
        Input PCM sample rate in Hz (default 12 000).
    quality_kbps:
        Opus target bit-rate in kbps (default 24).
    max_storage_mb:
        Hard storage ceiling in MiB.  Prune runs automatically when exceeded.
    retention_days:
        Recordings older than this many days are eligible for pruning.
    max_clip_sec:
        Maximum length of a single recording clip in seconds.  The recording is
        stopped automatically when the limit is reached.
    """

    def __init__(
        self,
        storage_path: str,
        sample_rate: int = 12_000,
        quality_kbps: int = 24,
        max_storage_mb: int = 10_240,
        retention_days: int = 30,
        max_clip_sec: int = 300,
    ):
        self.storage_path = Path(storage_path)
        self.sample_rate = sample_rate
        self.quality_kbps = quality_kbps
        self.max_storage_mb = max_storage_mb
        self.retention_days = retention_days
        self.max_clip_sec = max_clip_sec

        self._lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._current_path: str | None = None
        self._start_time: float | None = None
        self._use_ffmpeg: bool = _ffmpeg_available()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_recording(self, frequency_hz: int, mode: str) -> str:
        """Begin a new recording clip.

        Returns the path where the recording will be written.
        Any in-progress recording is stopped first.
        """
        with self._lock:
            if self._proc is not None:
                self._stop_locked()

            path = self._build_path(frequency_hz, mode)
            path.parent.mkdir(parents=True, exist_ok=True)

            if self._use_ffmpeg:
                self._proc = self._spawn_ffmpeg(path)
            else:
                # Fallback: open file for raw WAV writing
                self._proc = _WavWriter(path, self.sample_rate)
                self._proc.start()

            self._current_path = str(path)
            self._start_time = time.monotonic()
            logger.debug("Recording started: %s", self._current_path)
            return self._current_path

    def write_audio(self, samples: np.ndarray):
        """Push Float32 PCM samples into the active recording.

        Auto-stops when max_clip_sec is reached.
        """
        with self._lock:
            if self._proc is None or self._current_path is None:
                return

            # Enforce clip duration limit
            if self._start_time is not None:
                elapsed = time.monotonic() - self._start_time
                if elapsed >= self.max_clip_sec:
                    logger.debug("Max clip duration reached, stopping recording")
                    self._stop_locked()
                    return

            raw = samples.astype(np.float32).tobytes()
            try:
                self._proc.stdin.write(raw)
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError):
                logger.warning("ffmpeg pipe broken; discarding audio")
                self._proc = None

    def stop_recording(self) -> str:
        """Finalise the current recording and return its path."""
        with self._lock:
            return self._stop_locked()

    def prune_old_recordings(self):
        """Delete recordings that are past retention_days or push total over limit."""
        recordings_root = self.storage_path / "recordings"
        if not recordings_root.exists():
            return

        cutoff = datetime.now() - timedelta(days=self.retention_days)

        # Collect all .ogg and .wav files with their stats
        all_files: list[tuple[float, Path]] = []
        for f in recordings_root.rglob("*"):
            if f.is_file() and f.suffix in (".ogg", ".wav"):
                mtime = f.stat().st_mtime
                # Delete files beyond retention window immediately
                if datetime.fromtimestamp(mtime) < cutoff:
                    try:
                        f.unlink()
                        logger.debug("Pruned (age): %s", f)
                    except OSError:
                        pass
                else:
                    all_files.append((mtime, f))

        # Remove empty date directories
        for d in sorted(recordings_root.iterdir(), reverse=False):
            if d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except OSError:
                    pass

        # Enforce storage cap: delete oldest files first
        limit_bytes = self.max_storage_mb * 1024 * 1024
        all_files.sort(key=lambda x: x[0])  # oldest first
        while all_files:
            usage = self.get_storage_usage_mb() * 1024 * 1024
            if usage <= limit_bytes:
                break
            _, oldest = all_files.pop(0)
            try:
                oldest.unlink()
                logger.debug("Pruned (size): %s", oldest)
            except OSError:
                pass

    def get_storage_usage_mb(self) -> float:
        """Return total size of all recordings in MiB."""
        recordings_root = self.storage_path / "recordings"
        if not recordings_root.exists():
            return 0.0
        total = sum(
            f.stat().st_size
            for f in recordings_root.rglob("*")
            if f.is_file()
        )
        return total / (1024 * 1024)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _stop_locked(self) -> str:
        """Close ffmpeg stdin and wait for it to finish.  Caller holds _lock."""
        path = self._current_path or ""
        if self._proc is not None:
            try:
                self._proc.stdin.close()
            except OSError:
                pass
            try:
                self._proc.wait(timeout=10)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        self._current_path = None
        self._start_time = None
        logger.debug("Recording stopped: %s", path)
        return path

    def _build_path(self, frequency_hz: int, mode: str) -> Path:
        ts = datetime.now()
        date_dir = ts.strftime("%Y-%m-%d")
        timestamp = ts.strftime("%Y%m%dT%H%M%S")
        safe_mode = mode.replace(" ", "_").lower()
        ext = "ogg" if self._use_ffmpeg else "wav"
        filename = f"{timestamp}_{frequency_hz}_{safe_mode}.{ext}"
        return self.storage_path / "recordings" / date_dir / filename

    def _spawn_ffmpeg(self, output_path: Path) -> subprocess.Popen:
        """Start an ffmpeg process that reads raw float PCM from stdin."""
        cmd = [
            "ffmpeg",
            "-y",                          # overwrite without prompt
            "-f", "f32le",                 # input format: float32 little-endian
            "-ar", str(self.sample_rate),  # input sample rate
            "-ac", "1",                    # mono
            "-i", "pipe:0",               # read from stdin
            "-c:a", "libopus",
            "-b:a", f"{self.quality_kbps}k",
            "-vbr", "on",
            "-application", "voip",
            str(output_path),
        ]
        return subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


# ---------------------------------------------------------------------------
# WAV fallback writer (used when ffmpeg is absent, e.g. in CI)
# ---------------------------------------------------------------------------

class _WavWriter:
    """Minimal WAV file writer that mimics the Popen interface."""

    def __init__(self, path: Path, sample_rate: int):
        self._path = path
        self._sample_rate = sample_rate
        self._fh = None
        self._num_samples = 0
        self.stdin = self  # so caller can write to self.stdin

    def start(self):
        self._fh = open(self._path, "wb")
        self._write_wav_header(placeholder=True)

    # Mimic Popen.stdin.write / flush
    def write(self, data: bytes):
        if self._fh is None:
            return
        self._fh.write(data)
        self._num_samples += len(data) // 4  # float32 = 4 bytes

    def flush(self):
        if self._fh:
            self._fh.flush()

    def close(self):
        if self._fh is None:
            return
        # Rewrite the WAV header with correct sizes
        data_size = self._num_samples * 4  # float32
        self._fh.seek(0)
        self._write_wav_header(data_size=data_size)
        self._fh.close()
        self._fh = None

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass

    def _write_wav_header(self, placeholder: bool = False, data_size: int = 0):
        sample_rate = self._sample_rate
        num_channels = 1
        bits_per_sample = 32
        byte_rate = sample_rate * num_channels * bits_per_sample // 8
        block_align = num_channels * bits_per_sample // 8
        chunk_size = 36 + data_size if not placeholder else 0xFFFFFFFF

        self._fh.write(b"RIFF")
        self._fh.write(struct.pack("<I", chunk_size))
        self._fh.write(b"WAVE")
        self._fh.write(b"fmt ")
        self._fh.write(struct.pack("<I", 16))             # subchunk1 size
        self._fh.write(struct.pack("<H", 3))              # PCM float = 3
        self._fh.write(struct.pack("<H", num_channels))
        self._fh.write(struct.pack("<I", sample_rate))
        self._fh.write(struct.pack("<I", byte_rate))
        self._fh.write(struct.pack("<H", block_align))
        self._fh.write(struct.pack("<H", bits_per_sample))
        self._fh.write(b"data")
        self._fh.write(struct.pack("<I", data_size if not placeholder else 0xFFFFFFFF))
