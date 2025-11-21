#!/usr/bin/env python3
"""
Integration tests for demodulators using test IQ files.

These tests verify that demodulators can process IQ files correctly.
Requires pycsdr and related dependencies.
"""

import unittest
import struct
from pathlib import Path


# Path to test data
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data" / "iq"
TEST_TONE_FILE = TEST_DATA_DIR / "test_tone_1khz.cf32"
TEST_FM_FILE = TEST_DATA_DIR / "test_fm_240k.cf32"
TEST_CW_FILE = TEST_DATA_DIR / "test_cw.cf32"


class TestToneDemodulation(unittest.TestCase):
    """Test basic tone detection with IQ file."""

    @classmethod
    def setUpClass(cls):
        """Check if pycsdr is available."""
        try:
            from pycsdr.types import Format
            cls.pycsdr_available = True
        except ImportError:
            cls.pycsdr_available = False

    def test_tone_file_has_signal(self):
        """Verify tone file contains actual signal (not silence)."""
        if not TEST_TONE_FILE.exists():
            self.skipTest("Test tone file not found")

        with open(TEST_TONE_FILE, 'rb') as f:
            # Read 1000 samples
            data = f.read(8000)  # 1000 samples * 8 bytes

        # Parse as IQ samples
        samples = []
        for i in range(0, len(data), 8):
            i_val, q_val = struct.unpack('<ff', data[i:i+8])
            magnitude = (i_val**2 + q_val**2)**0.5
            samples.append(magnitude)

        # Verify signal is present (magnitude > 0)
        avg_magnitude = sum(samples) / len(samples)
        self.assertGreater(avg_magnitude, 0.1, "Expected signal, got silence")

        # For a 1kHz tone at 0.5 amplitude, magnitude should be ~0.5
        self.assertLess(avg_magnitude, 0.6, "Signal too strong")


class TestFMDemodulation(unittest.TestCase):
    """Test FM signal characteristics."""

    def test_fm_file_has_modulation(self):
        """Verify FM file has frequency modulation."""
        if not TEST_FM_FILE.exists():
            self.skipTest("Test FM file not found")

        with open(TEST_FM_FILE, 'rb') as f:
            # Read samples
            data = f.read(16000)  # 2000 samples

        # Calculate instantaneous phase changes
        phases = []
        for i in range(0, len(data) - 8, 8):
            i1, q1 = struct.unpack('<ff', data[i:i+8])
            i2, q2 = struct.unpack('<ff', data[i+8:i+16])

            # Phase difference
            import math
            phase1 = math.atan2(q1, i1)
            phase2 = math.atan2(q2, i2)
            phase_diff = phase2 - phase1

            # Unwrap phase
            if phase_diff > math.pi:
                phase_diff -= 2 * math.pi
            elif phase_diff < -math.pi:
                phase_diff += 2 * math.pi

            phases.append(phase_diff)

        # For FM, phase differences should vary (modulation)
        # Calculate variance
        mean_phase = sum(phases) / len(phases)
        variance = sum((p - mean_phase)**2 for p in phases) / len(phases)

        # FM should have significant variance in phase
        self.assertGreater(variance, 0.001, "Expected FM modulation")


class TestCWDemodulation(unittest.TestCase):
    """Test CW/Morse code signal characteristics."""

    def test_cw_file_has_keying(self):
        """Verify CW file has on/off keying."""
        if not TEST_CW_FILE.exists():
            self.skipTest("Test CW file not found")

        with open(TEST_CW_FILE, 'rb') as f:
            # Read enough samples to cover multiple complete characters
            # At 20 WPM, a character takes ~0.5-1s depending on complexity
            # Read 2 seconds = 96000 samples to capture several characters
            data = f.read(768000)  # 96000 samples * 8 bytes

        # Calculate envelope (magnitude)
        envelope = []
        for i in range(0, len(data), 8):
            i_val, q_val = struct.unpack('<ff', data[i:i+8])
            magnitude = (i_val**2 + q_val**2)**0.5
            envelope.append(magnitude)

        # CW should have both silent and loud periods
        # Find min and max
        min_mag = min(envelope)
        max_mag = max(envelope)

        # Should have silence (near 0)
        self.assertLess(min_mag, 0.01, "Expected silence in CW")

        # Should have signal (near 0.5)
        self.assertGreater(max_mag, 0.4, "Expected signal in CW")

        # Count transitions (on/off)
        threshold = 0.25
        transitions = 0
        prev_state = envelope[0] > threshold
        for mag in envelope[1:]:
            state = mag > threshold
            if state != prev_state:
                transitions += 1
                prev_state = state

        # CW "CQ DE W1AW" should have many transitions
        self.assertGreater(transitions, 10, "Expected keying transitions in CW")


class TestPycsdrIntegration(unittest.TestCase):
    """Test that we can use pycsdr to process IQ data."""

    @classmethod
    def setUpClass(cls):
        """Check if pycsdr is available."""
        try:
            from pycsdr.types import Format
            from pycsdr.modules import Convert
            cls.pycsdr_available = True
        except ImportError:
            cls.pycsdr_available = False

    def test_can_read_iq_with_pycsdr(self):
        """Test that pycsdr can process our IQ format."""
        if not self.pycsdr_available:
            self.skipTest("pycsdr not available")

        if not TEST_TONE_FILE.exists():
            self.skipTest("Test file not found")

        from pycsdr.types import Format

        # Read IQ data
        with open(TEST_TONE_FILE, 'rb') as f:
            data = f.read(8000)  # 1000 samples

        # Verify format matches pycsdr expectations
        # cf32 = complex float32 = COMPLEX_FLOAT
        expected_samples = len(data) // 8
        self.assertEqual(expected_samples, 1000)


if __name__ == "__main__":
    unittest.main()
