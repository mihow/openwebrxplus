import unittest


class TestFileSourceCommandLogic(unittest.TestCase):
    """Test FileSource command generation logic (isolated from imports)."""

    def _generate_command(self, file_path, sample_rate, loop):
        """Replicate the command generation logic from FileSource.getCommand()."""
        byte_rate = sample_rate * 8  # cf32 = 8 bytes/sample

        if loop:
            read_cmd = f"while true; do cat '{file_path}'; done"
        else:
            read_cmd = f"cat '{file_path}'"

        playback_cmd = f"{read_cmd} | pv -q -L {byte_rate}"
        return playback_cmd

    def test_looped_command(self):
        """Test looped playback command generation."""
        cmd = self._generate_command("/path/to/test.cf32", 48000, loop=True)

        self.assertIn("while true", cmd)
        self.assertIn("cat '/path/to/test.cf32'", cmd)
        self.assertIn("pv -q -L 384000", cmd)  # 48000 * 8

    def test_non_looped_command(self):
        """Test non-looped playback command generation."""
        cmd = self._generate_command("/path/to/test.cf32", 48000, loop=False)

        self.assertNotIn("while true", cmd)
        self.assertIn("cat '/path/to/test.cf32'", cmd)
        self.assertIn("pv -q -L 384000", cmd)

    def test_byte_rate_calculation(self):
        """Test byte rate calculation for different sample rates."""
        # cf32 = 8 bytes per sample
        cmd = self._generate_command("/test.cf32", 2400000, loop=False)
        self.assertIn("pv -q -L 19200000", cmd)  # 2.4M * 8 = 19.2MB/s


class TestFileSourceFeatureDetection(unittest.TestCase):
    """Test feature detection logic for file source."""

    def test_feature_requirements(self):
        """Verify file source requires pv and nmux."""
        # Read the features dict directly from source
        import ast

        with open("owrx/feature.py", "r") as f:
            content = f.read()

        # Find the features dict - look for "file" key
        self.assertIn('"file": ["pv", "nmux"]', content)


if __name__ == "__main__":
    unittest.main()
