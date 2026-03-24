"""Scanner service — orchestrates sweeper, detector, classifier, and database.

Runs a background thread that sweeps frequencies, detects signals,
classifies them, and logs results. Pure Python — no OpenWebRX+ imports.
SDR interaction is handled via callbacks (retune_callback, fft_callback).
"""

import logging
import threading
import time

import numpy as np

from owrx.scanner.classifier import ClassificationPipeline
from owrx.scanner.db import ScannerDatabase
from owrx.scanner.detector import SignalDetector
from owrx.scanner.known_freqs import match_known_freq
from owrx.scanner.recorder import ScannerRecorder
from owrx.scanner.sweep import FrequencySweeper

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "freq_start": 25_000_000,
    "freq_stop": 960_000_000,
    "sample_rate": 2_400_000,
    "fft_size": 1024,
    "snr_threshold_db": 10.0,
    "dwell_time": 0.5,
    "usable_bw_ratio": 0.8,
    "skip_ranges": [],
    "db_path": ":memory:",
}


class ScannerState:
    """Observable state container for the scanner UI."""

    IDLE = "idle"
    SCANNING = "scanning"
    LISTENING = "listening"
    PAUSED = "paused"

    def __init__(self):
        self.status: str = self.IDLE
        self.current_freq: int = 0
        self.current_mode: str = ""
        self.current_label: str = ""
        self.signal_strength: float = 0.0
        self.scan_progress: float = 0.0
        self.active_signals: list[dict] = []
        self._listeners: list = []

    def add_listener(self, callback):
        self._listeners.append(callback)

    def remove_listener(self, callback):
        self._listeners = [cb for cb in self._listeners if cb is not callback]

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        state_dict = self.to_dict()
        for cb in self._listeners:
            try:
                cb(state_dict)
            except Exception:
                logger.exception("Error in state listener callback")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "current_freq": self.current_freq,
            "current_mode": self.current_mode,
            "current_label": self.current_label,
            "signal_strength": self.signal_strength,
            "scan_progress": self.scan_progress,
            "active_signals": self.active_signals,
        }


class ScannerService:
    """Main scanner orchestrator. Singleton."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.state = ScannerState()
        self.db: ScannerDatabase | None = None
        self._sdr_source = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._hold_freq: int | None = None
        self._session_id: int | None = None
        self._sweeper: FrequencySweeper | None = None
        self._detector: SignalDetector | None = None
        self._classifier: ClassificationPipeline | None = None
        self._retune_callback = None
        self._fft_callback = None
        self._dwell_time: float = 0.5
        self._bridge = None
        self._recorder: ScannerRecorder | None = None

    def start_with_sdr(self, sdr_source, config: dict | None = None):
        """Start scanning using a live OpenWebRX+ SdrSource.

        Creates an SdrBridge to connect to the SDR's FftChain and
        provides retune/fft callbacks automatically.
        """
        from owrx.scanner.sdr_bridge import SdrBridge

        cfg = {**DEFAULT_CONFIG, **(config or {})}

        # Pull scanner config from OpenWebRX+ config system if not overridden
        try:
            from owrx.config import Config
            pm = Config.get()
            for key in ("scanner_storage_path", "scanner_max_storage_mb",
                        "scanner_retention_days", "scanner_max_clip_sec"):
                if key not in cfg and key in pm:
                    cfg[key] = pm[key]
        except Exception:
            pass

        # Use persistent DB in the data directory when running with SDR
        if cfg.get("db_path") == ":memory:":
            cfg["db_path"] = "/var/lib/openwebrx/scanner.db"
        fft_size = cfg.get("fft_size", 1024)

        self._bridge = SdrBridge(sdr_source, fft_size=fft_size)
        self._bridge.start()

        # Override sample_rate from actual hardware
        cfg["sample_rate"] = self._bridge.get_sample_rate()

        self.start(
            sdr_source=sdr_source,
            config=cfg,
            retune_callback=self._bridge.retune,
            fft_callback=self._bridge.get_fft,
        )

    def start(self, sdr_source=None, config: dict | None = None,
              retune_callback=None, fft_callback=None):
        """Initialize components and start the scan loop thread."""
        cfg = {**DEFAULT_CONFIG, **(config or {})}

        self._sdr_source = sdr_source
        self._retune_callback = retune_callback
        self._fft_callback = fft_callback
        self._dwell_time = cfg["dwell_time"]

        self._sweeper = FrequencySweeper(
            freq_start=cfg["freq_start"],
            freq_stop=cfg["freq_stop"],
            sample_rate=cfg["sample_rate"],
            usable_bw_ratio=cfg["usable_bw_ratio"],
            skip_ranges=cfg["skip_ranges"],
        )
        self._detector = SignalDetector(
            fft_size=cfg["fft_size"],
            sample_rate=cfg["sample_rate"],
            snr_threshold_db=cfg["snr_threshold_db"],
        )
        self._classifier = ClassificationPipeline()
        self.db = ScannerDatabase(cfg["db_path"])
        self._session_id = self.db.start_session(cfg)

        storage_path = cfg.get("scanner_storage_path")
        if storage_path:
            self._recorder = ScannerRecorder(
                storage_path=storage_path,
                sample_rate=cfg.get("scanner_recording_sample_rate", 12_000),
                max_storage_mb=cfg.get("scanner_max_storage_mb", 10_240),
                retention_days=cfg.get("scanner_retention_days", 30),
                max_clip_sec=cfg.get("scanner_max_clip_sec", 300),
            )

        self._stop_event.clear()
        self._hold_freq = None
        self.state.update(status=ScannerState.SCANNING)

        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        logger.info("Scanner started (session %s)", self._session_id)

    def stop(self):
        """Stop the scan loop and clean up."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._bridge is not None:
            self._bridge.stop()
            self._bridge = None
        if self._session_id is not None and self.db is not None:
            self.db.stop_session(self._session_id)
            self._session_id = None
        if self._recorder is not None:
            self._recorder.stop_recording()
            self._recorder = None
        self.state.update(status=ScannerState.IDLE)
        logger.info("Scanner stopped")

    def pause(self):
        self.state.update(status=ScannerState.PAUSED)

    def resume(self):
        self.state.update(status=ScannerState.SCANNING)

    def skip(self):
        """Clear hold and resume scanning."""
        self._hold_freq = None
        self.state.update(status=ScannerState.SCANNING)

    def hold(self, freq_hz: int | None = None):
        """Hold on a frequency (or current frequency if None)."""
        if freq_hz is not None:
            self._hold_freq = freq_hz
        elif self.state.current_freq:
            self._hold_freq = self.state.current_freq

        # Retune SDR with offset to avoid DC spike
        if self._hold_freq and self._retune_callback:
            try:
                tuning = self._calculate_offset_tuning(self._hold_freq)
                self._retune_callback(tuning["sdr_center"])
                logger.info(
                    "Scanner: retuned SDR to %d (offset %d) for signal %d",
                    tuning["sdr_center"], tuning["offset_freq"], self._hold_freq,
                )
            except Exception:
                logger.exception("Scanner: retune for hold failed")

        # Update state with held frequency and appropriate mode
        updates = {"status": ScannerState.LISTENING}
        if self._hold_freq:
            updates["current_freq"] = self._hold_freq
            from owrx.scanner.sweep import demod_mode_for_freq
            updates["current_mode"] = demod_mode_for_freq(self._hold_freq)
        self.state.update(**updates)

    def _scan_loop(self):
        """Background thread: sweep, detect, classify, log."""
        while not self._stop_event.is_set():
            # Paused — sleep and retry
            if self.state.status == ScannerState.PAUSED:
                time.sleep(0.1)
                continue

            # Holding on a frequency — sleep and retry
            if self._hold_freq is not None:
                time.sleep(0.1)
                continue

            if self._sweeper is None:
                break

            # Get current window
            window = self._sweeper.current_window()
            center_freq = window["center_freq"]

            # Update state
            self.state.update(
                current_freq=center_freq,
                current_mode=window["demod_mode"],
                scan_progress=self._sweeper.progress,
            )

            # Retune SDR
            if self._retune_callback is not None:
                try:
                    self._retune_callback(center_freq)
                except Exception:
                    logger.exception("Retune callback failed")

            # Dwell
            self._stop_event.wait(self._dwell_time)
            if self._stop_event.is_set():
                break

            # Get FFT data and detect signals
            if self._fft_callback is not None:
                try:
                    fft_data = self._fft_callback()
                except Exception:
                    logger.exception("FFT callback failed")
                    fft_data = None

                if fft_data is not None and self._detector is not None:
                    signals = self._detector.detect(fft_data, center_freq)
                    self.state.update(active_signals=signals)

                    # Classify and log each detection
                    for sig in signals:
                        if self._classifier is not None:
                            freq_hz = int(sig["frequency_hz"])
                            result = self._classifier.classify(
                                frequency_hz=freq_hz,
                                bandwidth_hz=sig["bandwidth_hz"],
                                peak_power_db=sig["peak_power_db"],
                                snr_db=sig["snr_db"],
                            )
                            label = match_known_freq(freq_hz)

                            # Record marker tone if no live DSP recording
                            # (live SDR recording happens in connection.py via DSP tap)
                            recording_path = None
                            if self._recorder is not None and self._bridge is None:
                                try:
                                    recording_path = self._record_signal(
                                        freq_hz, result["mode"],
                                    )
                                except Exception:
                                    logger.exception("Recording failed for %d", freq_hz)

                            if self.db is not None:
                                self.db.log_detection(
                                    frequency_hz=freq_hz,
                                    bandwidth_hz=int(sig["bandwidth_hz"]),
                                    mode=result["mode"],
                                    peak_power_db=sig["peak_power_db"],
                                    snr_db=sig["snr_db"],
                                    classification=result["classification"],
                                    filter_result=result["filter_result"],
                                    bookmark_label=label,
                                    recording_path=recording_path,
                                )

            # Advance to next window
            self._sweeper.advance()

    def _record_signal(self, freq_hz: int, mode: str) -> str | None:
        """Record a short audio clip for a detected signal.

        Generates a brief marker tone (the scan loop doesn't have IQ data).
        Real audio recording happens in the DSP chain path (connection.py).
        """
        if self._recorder is None:
            return None

        path = self._recorder.start_recording(freq_hz, mode)

        # Generate a 0.5-second marker tone at the detection frequency
        # (modulo audible range) so recordings are distinguishable
        sr = self._recorder.sample_rate
        duration = 0.5
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        tone_hz = 300 + (freq_hz % 700)  # map to 300-1000 Hz
        samples = (0.3 * np.sin(2 * np.pi * tone_hz * t)).astype(np.float32)
        self._recorder.write_audio(samples)
        self._recorder.stop_recording()

        return path

    @staticmethod
    def _calculate_offset_tuning(
        signal_freq_hz: int, offset_hz: int = 100_000,
    ) -> dict:
        """Calculate SDR center frequency and DSP offset to avoid DC spike.

        Retunes the SDR below the signal by offset_hz, so the signal appears
        at a positive offset in the passband (away from the DC spike at center).

        Returns dict with 'sdr_center' and 'offset_freq'.
        """
        sdr_center = signal_freq_hz - offset_hz
        return {
            "sdr_center": sdr_center,
            "offset_freq": signal_freq_hz - sdr_center,  # == offset_hz
        }
