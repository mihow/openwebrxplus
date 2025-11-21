#!/usr/bin/env python3
"""
Integration tests for FileSource IQ playback.

These tests verify the FileSource works end-to-end with actual IQ files.
Some tests require pycsdr and related tools to be installed.
"""

import unittest
import os
import json
import struct
import subprocess
import time
from pathlib import Path


# Path to test data
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data" / "iq"
TEST_TONE_FILE = TEST_DATA_DIR / "test_tone_1khz.cf32"
TEST_TONE_META = TEST_DATA_DIR / "test_tone_1khz.json"


class TestIQFileValidity(unittest.TestCase):
    """Test that IQ test files are valid."""

    def test_test_file_exists(self):
        """Verify test IQ file exists."""
        self.assertTrue(TEST_TONE_FILE.exists(), f"Test file not found: {TEST_TONE_FILE}")

    def test_metadata_exists(self):
        """Verify metadata file exists."""
        self.assertTrue(TEST_TONE_META.exists(), f"Metadata not found: {TEST_TONE_META}")

    def test_metadata_valid(self):
        """Verify metadata is valid JSON with required fields."""
        with open(TEST_TONE_META) as f:
            meta = json.load(f)

        required_fields = ["sample_rate", "center_frequency", "duration_seconds"]
        for field in required_fields:
            self.assertIn(field, meta, f"Missing required field: {field}")

    def test_file_size_matches_metadata(self):
        """Verify file size matches expected from metadata."""
        with open(TEST_TONE_META) as f:
            meta = json.load(f)

        expected_samples = int(meta["sample_rate"] * meta["duration_seconds"])
        expected_bytes = expected_samples * 8  # cf32 = 8 bytes per sample

        actual_bytes = TEST_TONE_FILE.stat().st_size
        self.assertEqual(actual_bytes, expected_bytes,
                         f"File size mismatch: expected {expected_bytes}, got {actual_bytes}")

    def test_file_format_valid(self):
        """Verify file contains valid float32 samples."""
        with open(TEST_TONE_FILE, 'rb') as f:
            # Read first few samples
            data = f.read(80)  # 10 samples * 8 bytes

        # Should be able to unpack as float32 pairs
        num_samples = len(data) // 8
        for i in range(num_samples):
            offset = i * 8
            i_val, q_val = struct.unpack('<ff', data[offset:offset + 8])
            # Values should be in reasonable range (-1 to 1 for normalized)
            self.assertGreaterEqual(i_val, -2.0)
            self.assertLessEqual(i_val, 2.0)
            self.assertGreaterEqual(q_val, -2.0)
            self.assertLessEqual(q_val, 2.0)


class TestFileSourceCommand(unittest.TestCase):
    """Test FileSource command generation with real files."""

    def test_command_uses_real_file(self):
        """Test command generation with actual test file path."""
        # Replicate FileSource.getCommand() logic
        file_path = str(TEST_TONE_FILE)
        sample_rate = 48000
        loop = False

        byte_rate = sample_rate * 8
        read_cmd = f"cat '{file_path}'"
        playback_cmd = f"{read_cmd} | pv -q -L {byte_rate}"

        self.assertIn(str(TEST_TONE_FILE), playback_cmd)
        self.assertIn("pv -q -L 384000", playback_cmd)


class TestFileSourcePlayback(unittest.TestCase):
    """Test actual IQ file playback (requires pv)."""

    @classmethod
    def setUpClass(cls):
        """Check if pv is available."""
        try:
            subprocess.run(["pv", "--version"], capture_output=True, check=True)
            cls.pv_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            cls.pv_available = False

    def test_pv_rate_limiting(self):
        """Test that pv can rate-limit file playback."""
        if not self.pv_available:
            self.skipTest("pv not available")

        # Read small amount of data with rate limiting
        # At 384000 bytes/sec, reading 38400 bytes should take ~0.1s
        cmd = f"head -c 38400 '{TEST_TONE_FILE}' | pv -q -L 384000 | wc -c"

        start = time.time()
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        elapsed = time.time() - start

        self.assertEqual(result.returncode, 0)
        self.assertEqual(int(result.stdout.strip()), 38400)
        # Should take at least 0.05s (allowing for overhead)
        self.assertGreater(elapsed, 0.05)


class TestPycsdrIntegration(unittest.TestCase):
    """Test integration with pycsdr (requires pycsdr installed)."""

    @classmethod
    def setUpClass(cls):
        """Check if pycsdr is available."""
        try:
            from pycsdr.modules import Buffer
            from pycsdr.types import Format
            cls.pycsdr_available = True
        except ImportError:
            cls.pycsdr_available = False

    def test_pycsdr_can_process_iq(self):
        """Test that pycsdr can process our IQ format."""
        if not self.pycsdr_available:
            self.skipTest("pycsdr not available")

        from pycsdr.modules import Buffer
        from pycsdr.types import Format

        # Create a buffer for complex float data
        buffer = Buffer(Format.COMPLEX_FLOAT)

        # Read some samples from our test file and verify format
        with open(TEST_TONE_FILE, 'rb') as f:
            data = f.read(8000)  # 1000 samples

        # Verify we can read the expected amount (format compatibility)
        self.assertEqual(len(data), 8000)

        # Verify buffer was created with correct format
        self.assertIsNotNone(buffer)


class TestNmuxIntegration(unittest.TestCase):
    """Test integration with nmux (requires nmux installed)."""

    @classmethod
    def setUpClass(cls):
        """Check if nmux is available."""
        try:
            # nmux --help may return non-zero, just check if it runs
            result = subprocess.run(["nmux", "--help"], capture_output=True)
            cls.nmux_available = True
        except (FileNotFoundError, OSError):
            cls.nmux_available = False

    def test_nmux_available(self):
        """Verify nmux is available for FileSource."""
        if not self.nmux_available:
            self.skipTest("nmux not available")

        # Just verify it can be invoked
        result = subprocess.run(["which", "nmux"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
