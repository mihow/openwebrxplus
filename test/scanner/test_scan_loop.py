import os
import unittest
import tempfile
import time
import numpy as np


class TestScanLoop(unittest.TestCase):
    """Test ScannerService._scan_loop() with synthetic FFT data."""

    def test_scan_loop_detects_signal(self):
        """Scan loop should detect a synthetic signal and log it to DB."""
        from owrx.scanner import ScannerService

        svc = ScannerService()

        # Synthetic FFT: noise at -90 dB with a signal at bins 500-520
        fft_data = np.full(1024, -90.0, dtype=np.float32)
        fft_data[500:520] = -50.0  # 40 dB above noise

        call_count = [0]
        def mock_fft():
            call_count[0] += 1
            if call_count[0] > 5:
                return None  # Stop producing data
            return fft_data

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        svc.start(
            config={
                "freq_start": 100000000,
                "freq_stop": 110000000,
                "sample_rate": 2400000,
                "dwell_time": 0.05,
                "fft_size": 1024,
                "db_path": db_path,
            },
            retune_callback=lambda f: None,
            fft_callback=mock_fft,
        )

        time.sleep(1)
        svc.stop()

        # Should have logged detections
        detections = svc.db.get_recent_detections(limit=50)
        self.assertGreater(len(detections), 0, "Expected at least 1 detection")
        # First detection should have reasonable frequency
        det = detections[0]
        self.assertIsNotNone(det.get("frequency_hz"))
        self.assertIsNotNone(det.get("mode"))

        import os
        os.unlink(db_path)

    def test_scan_loop_no_signals_in_noise(self):
        """Scan loop should detect nothing in pure noise."""
        from owrx.scanner import ScannerService

        svc = ScannerService()

        # Pure noise, no signals
        fft_data = np.full(1024, -90.0, dtype=np.float32)

        call_count = [0]
        def mock_fft():
            call_count[0] += 1
            if call_count[0] > 3:
                return None
            return fft_data

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        svc.start(
            config={
                "freq_start": 100000000,
                "freq_stop": 110000000,
                "sample_rate": 2400000,
                "dwell_time": 0.05,
                "fft_size": 1024,
                "db_path": db_path,
            },
            retune_callback=lambda f: None,
            fft_callback=mock_fft,
        )

        time.sleep(0.5)
        svc.stop()

        detections = svc.db.get_recent_detections(limit=50)
        self.assertEqual(len(detections), 0, "Expected 0 detections in noise")

        import os
        os.unlink(db_path)

    def test_scan_loop_hold_stops_sweep(self):
        """hold() should stop the sweep and keep current frequency."""
        from owrx.scanner import ScannerService, ScannerState

        svc = ScannerService()
        fft_data = np.full(1024, -90.0, dtype=np.float32)

        retune_freqs = []
        def mock_retune(f):
            retune_freqs.append(f)

        def mock_fft():
            return fft_data

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        svc.start(
            config={
                "freq_start": 100000000,
                "freq_stop": 110000000,
                "sample_rate": 2400000,
                "dwell_time": 0.05,
                "fft_size": 1024,
                "db_path": db_path,
            },
            retune_callback=mock_retune,
            fft_callback=mock_fft,
        )

        time.sleep(0.3)
        svc.hold(105000000)
        retune_count_at_hold = len(retune_freqs)
        time.sleep(0.3)
        retune_count_after = len(retune_freqs)

        svc.stop()

        # After hold, retune should have been called once more (for the hold freq)
        # but sweep should have stopped (no more retune calls)
        self.assertLessEqual(
            retune_count_after - retune_count_at_hold, 2,
            "Sweep should stop after hold()"
        )
        self.assertEqual(svc.state.status, ScannerState.IDLE)  # after stop

        import os
        os.unlink(db_path)

    def test_scan_loop_auto_listens_on_strong_signal(self):
        """Scan loop should auto-hold on strong signals to record."""
        from owrx.scanner import ScannerService, ScannerState

        svc = ScannerService()

        # Synthetic FFT: strong signal at bins 500-520 (40 dB SNR)
        fft_data = np.full(1024, -90.0, dtype=np.float32)
        fft_data[500:520] = -50.0

        call_count = [0]
        def mock_fft():
            call_count[0] += 1
            if call_count[0] > 5:
                return None
            return fft_data

        # Track state transitions
        states_seen = []
        def state_listener(state_dict):
            states_seen.append(state_dict["status"])

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        svc.start(
            config={
                "freq_start": 100_000_000,
                "freq_stop": 110_000_000,
                "sample_rate": 2_400_000,
                "dwell_time": 0.05,
                "fft_size": 1024,
                "db_path": db_path,
                "listen_time": 0.5,  # short for testing
                "listen_threshold": 10.0,
            },
            retune_callback=lambda f: None,
            fft_callback=mock_fft,
        )
        svc.state.add_listener(state_listener)

        time.sleep(3)
        svc.stop()

        # Should have detected signals and auto-listened
        detections = svc.db.get_recent_detections(limit=50)
        self.assertGreater(len(detections), 0, "Expected at least 1 detection")

        # Should have transitioned through LISTENING at some point
        self.assertIn("listening", states_seen,
                       "Scanner should have auto-held on a signal")

    def test_scan_loop_no_recording_in_noise(self):
        """No recordings should be created when only noise is present."""
        import tempfile
        from pathlib import Path
        from owrx.scanner import ScannerService

        svc = ScannerService()
        fft_data = np.full(1024, -90.0, dtype=np.float32)

        call_count = [0]
        def mock_fft():
            call_count[0] += 1
            if call_count[0] > 3:
                return None
            return fft_data

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            storage_path = os.path.join(tmpdir, "storage")

            svc.start(
                config={
                    "freq_start": 100_000_000,
                    "freq_stop": 110_000_000,
                    "sample_rate": 2_400_000,
                    "dwell_time": 0.05,
                    "fft_size": 1024,
                    "db_path": db_path,
                    "scanner_storage_path": storage_path,
                },
                retune_callback=lambda f: None,
                fft_callback=mock_fft,
            )

            time.sleep(0.5)
            svc.stop()

            recordings_dir = Path(storage_path) / "recordings"
            if recordings_dir.exists():
                files = list(recordings_dir.rglob("*.*"))
                assert len(files) == 0, f"Expected no recordings, found: {files}"


if __name__ == "__main__":
    unittest.main()
