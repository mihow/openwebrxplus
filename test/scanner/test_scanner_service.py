"""Tests for ScannerState and ScannerService command methods."""

from owrx.scanner import ScannerState, ScannerService


class TestScannerState:
    def test_state_initial(self):
        state = ScannerState()
        assert state.status == ScannerState.IDLE
        assert state.current_freq == 0

    def test_state_update_notifies_listeners(self):
        state = ScannerState()
        received = []
        state.add_listener(lambda d: received.append(d))
        state.update(status=ScannerState.SCANNING, current_freq=100_000_000)
        assert len(received) == 1
        assert received[0]["status"] == ScannerState.SCANNING
        assert received[0]["current_freq"] == 100_000_000

    def test_state_to_dict(self):
        state = ScannerState()
        d = state.to_dict()
        expected_keys = {
            "status",
            "current_freq",
            "current_mode",
            "current_label",
            "signal_strength",
            "scan_progress",
            "active_signals",
        }
        assert set(d.keys()) == expected_keys

    def test_hold_and_skip(self):
        svc = ScannerService()
        svc.hold(145_000_000)
        assert svc._hold_freq == 145_000_000
        assert svc.state.status == ScannerState.LISTENING
        svc.skip()
        assert svc._hold_freq is None
        assert svc.state.status == ScannerState.SCANNING

    def test_pause_and_resume(self):
        svc = ScannerService()
        svc.pause()
        assert svc.state.status == ScannerState.PAUSED
        svc.resume()
        assert svc.state.status == ScannerState.SCANNING
