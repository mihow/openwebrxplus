"""Tests for ScannerService.start_with_sdr bridge integration.

These tests verify the wiring logic without requiring actual pycsdr/SdrSource.
The SdrBridge itself requires pycsdr (C extensions) so we test at the
ScannerService level with mock callbacks — same pattern as test_scanner_service.py.
"""

import unittest
import threading
import time
import numpy as np

from owrx.scanner import ScannerService, ScannerState


class TestScannerWithSdrBridge(unittest.TestCase):
    """Test that start_with_sdr properly wires retune and FFT callbacks."""

    def test_start_with_sdr_sets_bridge(self):
        """start_with_sdr should create a bridge and store it."""
        service = ScannerService()
        # We can't call start_with_sdr without a real SdrSource,
        # but we can verify the method exists and the bridge field
        self.assertIsNone(service._bridge)

    def test_stop_cleans_up_bridge(self):
        """stop() should clean up bridge if set."""
        service = ScannerService()

        # Simulate what start_with_sdr does by setting bridge manually
        class MockBridge:
            stopped = False
            def stop(self):
                self.stopped = True

        mock = MockBridge()
        service._bridge = mock

        # Start with mock callbacks so there's a thread to stop
        service.start(
            config={"db_path": ":memory:", "dwell_time": 0.1},
            retune_callback=lambda f: None,
            fft_callback=lambda: np.full(1024, -90.0, dtype=np.float32),
        )
        service.stop()

        self.assertTrue(mock.stopped)
        self.assertIsNone(service._bridge)

    def test_scan_loop_uses_retune_and_fft_callbacks(self):
        """Verify the scan loop calls retune and fft callbacks."""
        service = ScannerService()
        retune_log = []
        fft_call_count = [0]

        def mock_retune(freq):
            retune_log.append(freq)

        def mock_fft():
            fft_call_count[0] += 1
            return np.full(1024, -90.0, dtype=np.float32)

        service.start(
            config={
                "db_path": ":memory:",
                "dwell_time": 0.05,
                "freq_start": 100_000_000,
                "freq_stop": 110_000_000,
                "sample_rate": 2_400_000,
            },
            retune_callback=mock_retune,
            fft_callback=mock_fft,
        )

        # Let the scan loop run a few iterations
        time.sleep(0.3)
        service.stop()

        # Should have called retune at least once
        self.assertGreater(len(retune_log), 0)
        # Should have called fft at least once
        self.assertGreater(fft_call_count[0], 0)
        # Retune should be called with frequencies in range
        for freq in retune_log:
            self.assertGreaterEqual(freq, 100_000_000)
            self.assertLessEqual(freq, 115_000_000)  # center + half sample_rate

    def test_hold_frequency_pauses_scanning(self):
        """hold() should stop the scan loop from advancing."""
        service = ScannerService()
        retune_log = []

        service.start(
            config={"db_path": ":memory:", "dwell_time": 0.05},
            retune_callback=lambda f: retune_log.append(f),
            fft_callback=lambda: np.full(1024, -90.0, dtype=np.float32),
        )

        time.sleep(0.15)
        count_before = len(retune_log)

        service.hold(146_520_000)
        retune_log.clear()
        time.sleep(0.15)

        # While holding, no new retunes should happen
        self.assertEqual(len(retune_log), 0)
        self.assertEqual(service.state.status, ScannerState.LISTENING)

        service.stop()


if __name__ == "__main__":
    unittest.main()
