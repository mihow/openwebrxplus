"""Integration test: full scanner pipeline with simulated signals.

Exercises the complete flow: ScannerService → sweeper → detector →
classifier → known_freqs → database, using mock callbacks to simulate
SDR retune and FFT data with real-world signal characteristics.
"""

import time
import tempfile
import unittest

import numpy as np

from owrx.scanner import ScannerService, ScannerState
from owrx.scanner.known_freqs import match_known_freq


class TestFullScannerPipeline(unittest.TestCase):
    """End-to-end test with synthetic FFT data containing known signals."""

    def setUp(self):
        self.service = ScannerService()
        self.retune_log = []
        self.current_center_freq = 0

    def _retune(self, freq_hz):
        self.current_center_freq = freq_hz
        self.retune_log.append(freq_hz)

    def _make_fft_with_signal(self, signal_freq_hz, signal_power_db=-50.0,
                                noise_floor_db=-90.0, fft_size=1024,
                                sample_rate=2_400_000):
        """Generate an FFT array with a signal at a specific frequency."""
        fft = np.full(fft_size, noise_floor_db, dtype=np.float32)
        if signal_freq_hz is not None:
            # Convert signal freq to FFT bin index
            offset_hz = signal_freq_hz - self.current_center_freq
            bin_idx = int(fft_size / 2 + offset_hz / (sample_rate / fft_size))
            if 0 <= bin_idx < fft_size:
                # Make signal ~5 bins wide (typical NFM)
                for i in range(max(0, bin_idx - 2), min(fft_size, bin_idx + 3)):
                    fft[i] = signal_power_db
        return fft

    def _make_fft_callback(self, signals):
        """Create an FFT callback that returns signals based on center freq.

        signals: list of (freq_hz, power_db) tuples
        """
        def callback():
            for sig_freq, sig_power in signals:
                # Is this signal within the current FFT window?
                half_bw = 1_200_000  # half of 2.4 MHz
                if (self.current_center_freq - half_bw <= sig_freq <=
                        self.current_center_freq + half_bw):
                    return self._make_fft_with_signal(sig_freq, sig_power)
            # No signals in this window
            return self._make_fft_with_signal(None)
        return callback

    def test_detects_noaa_weather_signal(self):
        """Scanner should detect and label NOAA WX4 at 162.475 MHz."""
        fft_cb = self._make_fft_callback([
            (162_475_000, -50.0),  # NOAA WX4
        ])

        self.service.start(
            config={
                "db_path": ":memory:",
                "dwell_time": 0.02,
                "freq_start": 162_000_000,
                "freq_stop": 163_000_000,
                "sample_rate": 2_400_000,
                "fft_size": 1024,
                "snr_threshold_db": 10.0,
            },
            retune_callback=self._retune,
            fft_callback=fft_cb,
        )

        time.sleep(0.3)
        self.service.stop()

        # Should have detections in the database
        detections = self.service.db.get_recent_detections(limit=50)
        self.assertGreater(len(detections), 0)

        # Find the NOAA detection
        noaa = [d for d in detections if d.get("bookmark_label")
                and "NOAA" in d["bookmark_label"]]
        self.assertGreater(len(noaa), 0, "Should detect NOAA WX4")
        self.assertEqual(noaa[0]["mode"], "nfm")

    def test_detects_multiple_signals_across_bands(self):
        """Scanner should find signals across a wider scan range."""
        fft_cb = self._make_fft_callback([
            (146_520_000, -55.0),  # 2m simplex
            (162_475_000, -48.0),  # NOAA WX4
        ])

        self.service.start(
            config={
                "db_path": ":memory:",
                "dwell_time": 0.02,
                "freq_start": 145_000_000,
                "freq_stop": 163_000_000,
                "sample_rate": 2_400_000,
                "fft_size": 1024,
                "snr_threshold_db": 10.0,
            },
            retune_callback=self._retune,
            fft_callback=fft_cb,
        )

        time.sleep(0.5)
        self.service.stop()

        detections = self.service.db.get_recent_detections(limit=100)
        freqs_detected = set()
        for d in detections:
            # Round to nearest 100 kHz for matching
            rounded = round(d["frequency_hz"] / 100_000) * 100_000
            freqs_detected.add(rounded)

        self.assertIn(146_500_000, freqs_detected, "Should detect 2m simplex area")
        self.assertIn(162_500_000, freqs_detected, "Should detect NOAA area")

    def test_scan_progress_updates(self):
        """Scan progress should increase as windows are swept."""
        progress_values = []

        def track_state(state_dict):
            if state_dict.get("scan_progress", 0) > 0:
                progress_values.append(state_dict["scan_progress"])

        self.service.state.add_listener(track_state)

        fft_cb = self._make_fft_callback([])  # No signals, just sweep

        self.service.start(
            config={
                "db_path": ":memory:",
                "dwell_time": 0.02,
                "freq_start": 100_000_000,
                "freq_stop": 110_000_000,
                "sample_rate": 2_400_000,
            },
            retune_callback=self._retune,
            fft_callback=fft_cb,
        )

        time.sleep(0.3)
        self.service.stop()

        self.assertGreater(len(progress_values), 0, "Should have progress updates")
        # Progress should increase
        self.assertGreater(max(progress_values), 0)

    def test_known_freq_labels_in_database(self):
        """Detections should have bookmark_label from known_freqs."""
        fft_cb = self._make_fft_callback([
            (440_400_000, -52.0),  # W7RAT KOIN Tower
        ])

        self.service.start(
            config={
                "db_path": ":memory:",
                "dwell_time": 0.02,
                "freq_start": 440_000_000,
                "freq_stop": 441_000_000,
                "sample_rate": 2_400_000,
                "fft_size": 1024,
                "snr_threshold_db": 10.0,
            },
            retune_callback=self._retune,
            fft_callback=fft_cb,
        )

        time.sleep(0.3)
        self.service.stop()

        detections = self.service.db.get_recent_detections(limit=50)
        labeled = [d for d in detections if d.get("bookmark_label")]
        self.assertGreater(len(labeled), 0, "Should have labeled detections")
        # Check that W7RAT is in labels
        labels = [d["bookmark_label"] for d in labeled]
        self.assertTrue(
            any("W7RAT" in l for l in labels),
            f"Expected W7RAT in labels, got: {labels}"
        )

    def test_service_state_transitions(self):
        """Service should transition: idle → scanning → paused → scanning → idle."""
        self.assertEqual(self.service.state.status, ScannerState.IDLE)

        self.service.start(
            config={"db_path": ":memory:", "dwell_time": 0.05},
            retune_callback=self._retune,
            fft_callback=lambda: np.full(1024, -90.0, dtype=np.float32),
        )
        time.sleep(0.1)
        self.assertEqual(self.service.state.status, ScannerState.SCANNING)

        self.service.pause()
        self.assertEqual(self.service.state.status, ScannerState.PAUSED)

        self.service.resume()
        self.assertEqual(self.service.state.status, ScannerState.SCANNING)

        self.service.stop()
        self.assertEqual(self.service.state.status, ScannerState.IDLE)


if __name__ == "__main__":
    unittest.main()
