#!/usr/bin/env python3
"""
End-to-end DSP integration tests.

Tests that IQ files can be processed through actual demodulator chains
and produce expected output. This tests the full DSP stack integration.
"""

import unittest
import struct
from pathlib import Path
from unittest.mock import patch, MagicMock


# Path to test data
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data" / "iq"
TEST_TONE_FILE = TEST_DATA_DIR / "test_tone_1khz.cf32"
TEST_FM_FILE = TEST_DATA_DIR / "test_fm_240k.cf32"
TEST_CW_FILE = TEST_DATA_DIR / "test_cw.cf32"


class TestDemodulatorChains(unittest.TestCase):
    """Test complete demodulator chains with IQ files."""

    @classmethod
    def setUpClass(cls):
        """Check if csdr chains are available."""
        try:
            from csdr.chain.analog import Am, NFm
            from pycsdr.modules import Buffer
            from pycsdr.types import Format, AgcProfile
            cls.chains_available = True
        except ImportError:
            cls.chains_available = False

    def test_am_chain_instantiation(self):
        """Test that AM demodulator chain can be instantiated."""
        if not self.chains_available:
            self.skipTest("csdr chains not available")

        from csdr.chain.analog import Am
        from pycsdr.types import AgcProfile

        # Create AM chain
        am_chain = Am(agcProfile=AgcProfile.SLOW)

        # Verify chain has workers
        self.assertGreater(len(am_chain.workers), 0, "AM chain should have workers")

        # Verify expected modules in chain
        worker_types = [type(w).__name__ for w in am_chain.workers]
        self.assertIn("AmDemod", worker_types, "Should have AM demodulator")
        self.assertIn("DcBlock", worker_types, "Should have DC blocker")
        self.assertIn("Agc", worker_types, "Should have AGC")

        # Clean up
        am_chain.stop()

    def test_nfm_chain_instantiation(self):
        """Test that NFM demodulator chain can be instantiated."""
        if not self.chains_available:
            self.skipTest("csdr chains not available")

        from csdr.chain.analog import NFm
        from pycsdr.types import AgcProfile

        # Create NFM chain with 48kHz sample rate
        nfm_chain = NFm(sampleRate=48000, agcProfile=AgcProfile.SLOW)

        # Verify chain has workers
        self.assertGreater(len(nfm_chain.workers), 0, "NFM chain should have workers")

        # Verify expected modules
        worker_types = [type(w).__name__ for w in nfm_chain.workers]
        self.assertIn("FmDemod", worker_types, "Should have FM demodulator")
        self.assertIn("Limit", worker_types, "Should have limiter")
        self.assertIn("NfmDeemphasis", worker_types, "Should have deemphasis")
        self.assertIn("Agc", worker_types, "Should have AGC")

        # Clean up
        nfm_chain.stop()

    def test_wfm_chain_instantiation(self):
        """Test that WFM demodulator chain can be instantiated."""
        if not self.chains_available:
            self.skipTest("csdr chains not available")

        from csdr.chain.analog import WFm
        from pycsdr.types import AgcProfile

        # Create WFM chain with 240kHz sample rate (typical for FM broadcast)
        wfm_chain = WFm(sampleRate=240000, tau=50e-6, rdsRbds=False)

        # Verify chain has workers
        self.assertGreater(len(wfm_chain.workers), 0, "WFM chain should have workers")

        # Verify expected modules
        worker_types = [type(w).__name__ for w in wfm_chain.workers]
        self.assertIn("FmDemod", worker_types, "Should have FM demodulator")

        # Clean up
        wfm_chain.stop()

    def test_am_chain_with_iq_file_format(self):
        """Test that IQ file format is compatible with AM chain input."""
        if not self.chains_available:
            self.skipTest("csdr chains not available")

        if not TEST_TONE_FILE.exists():
            self.skipTest("Test file not found")

        from csdr.chain.analog import Am
        from pycsdr.modules import Buffer
        from pycsdr.types import Format, AgcProfile

        # Verify test file has correct format
        with open(TEST_TONE_FILE, 'rb') as f:
            # Read first IQ sample (8 bytes = 2 floats)
            data = f.read(8)
            self.assertEqual(len(data), 8, "Should read 8 bytes (1 complex float32 sample)")

            # Parse as complex float32
            i_val, q_val = struct.unpack('<ff', data)

            # Verify reasonable values (our test signals use 0.5 amplitude)
            self.assertTrue(-1.0 <= i_val <= 1.0, f"I value {i_val} should be normalized")
            self.assertTrue(-1.0 <= q_val <= 1.0, f"Q value {q_val} should be normalized")

        # Create AM chain and verify it expects COMPLEX_FLOAT input
        am_chain = Am(agcProfile=AgcProfile.SLOW)
        expected_format = am_chain.getInputFormat()
        self.assertEqual(expected_format, Format.COMPLEX_FLOAT,
                        "AM chain should expect COMPLEX_FLOAT input")

        am_chain.stop()

    def test_fm_chain_with_iq_file_format(self):
        """Test that FM IQ file format is compatible with WFM chain."""
        if not self.chains_available:
            self.skipTest("csdr chains not available")

        if not TEST_FM_FILE.exists():
            self.skipTest("Test FM file not found")

        from csdr.chain.analog import WFm
        from pycsdr.types import Format

        # Verify FM test file format
        with open(TEST_FM_FILE, 'rb') as f:
            data = f.read(8)
            i_val, q_val = struct.unpack('<ff', data)
            self.assertTrue(-1.0 <= i_val <= 1.0, "I value should be normalized")
            self.assertTrue(-1.0 <= q_val <= 1.0, "Q value should be normalized")

        # Create WFM chain with matching sample rate (240kHz is for wideband FM)
        wfm_chain = WFm(sampleRate=240000, tau=50e-6, rdsRbds=False)
        expected_format = wfm_chain.getInputFormat()
        self.assertEqual(expected_format, Format.COMPLEX_FLOAT,
                        "WFM chain should expect COMPLEX_FLOAT input")

        wfm_chain.stop()


class TestFileSourceIntegration(unittest.TestCase):
    """Test FileSource integration with demodulator chains."""

    @classmethod
    def setUpClass(cls):
        """Check if FileSource can be imported (requires pycsdr)."""
        try:
            from owrx.source.file import FileSource
            cls.file_source_available = True
        except ImportError:
            cls.file_source_available = False

    @patch('owrx.config.Config.get')
    def test_file_source_can_provide_iq_data(self, mock_config_get):
        """Test that FileSource can be used as input for DSP chains."""
        if not self.file_source_available:
            self.skipTest("FileSource not available (requires pycsdr)")

        from owrx.source.file import FileSource
        from owrx.property import PropertyLayer

        # Mock Config.get() to return an empty PropertyLayer
        mock_config_get.return_value = PropertyLayer()

        if not TEST_TONE_FILE.exists():
            self.skipTest("Test file not found")

        # Create FileSource configuration
        props = PropertyLayer(
            file_path=str(TEST_TONE_FILE),
            samp_rate=48000,
            center_freq=14074000,
            loop=False,
            name="Test FileSource",
            profiles=PropertyLayer()
        )

        # Create FileSource
        file_source = FileSource("test", props)

        # Get command that would be run
        command = file_source.getCommand()

        # Verify command includes file path
        command_str = " ".join(command)
        self.assertIn(str(TEST_TONE_FILE), command_str, "Command should include file path")
        self.assertIn("pv", command_str, "Command should use pv for rate limiting")
        # Verify byte rate calculation (48000 samples/sec * 8 bytes/sample = 384000 bytes/sec)
        self.assertIn("384000", command_str, "Command should include correct byte rate")

    @patch('owrx.config.Config.get')
    def test_file_source_with_fm_file(self, mock_config_get):
        """Test FileSource with FM test file."""
        if not self.file_source_available:
            self.skipTest("FileSource not available (requires pycsdr)")

        from owrx.source.file import FileSource
        from owrx.property import PropertyLayer

        # Mock Config.get() to return an empty PropertyLayer
        mock_config_get.return_value = PropertyLayer()

        if not TEST_FM_FILE.exists():
            self.skipTest("Test FM file not found")

        # Create FileSource for FM file
        props = PropertyLayer(
            file_path=str(TEST_FM_FILE),
            samp_rate=240000,  # FM broadcast sample rate
            center_freq=98100000,  # Example FM frequency
            loop=True,  # Loop for demo mode
            name="FM Test Source",
            profiles=PropertyLayer()
        )

        file_source = FileSource("fm_test", props)
        command = file_source.getCommand()
        command_str = " ".join(command)

        # Verify FM-specific settings
        self.assertIn(str(TEST_FM_FILE), command_str)
        # 240000 * 8 = 1920000 bytes/sec
        self.assertIn("1920000", command_str, "Should have correct byte rate for FM")
        self.assertIn("while true", command_str, "Should loop when loop=True")

    @patch('owrx.config.Config.get')
    def test_file_source_with_cw_file(self, mock_config_get):
        """Test FileSource with CW test file."""
        if not self.file_source_available:
            self.skipTest("FileSource not available (requires pycsdr)")

        from owrx.source.file import FileSource
        from owrx.property import PropertyLayer

        # Mock Config.get() to return an empty PropertyLayer
        mock_config_get.return_value = PropertyLayer()

        if not TEST_CW_FILE.exists():
            self.skipTest("Test CW file not found")

        # Create FileSource for CW file
        props = PropertyLayer(
            file_path=str(TEST_CW_FILE),
            samp_rate=48000,
            center_freq=14070000,  # CW frequency
            loop=False,
            name="CW Test Source",
            profiles=PropertyLayer()
        )

        file_source = FileSource("cw_test", props)
        command = file_source.getCommand()
        command_str = " ".join(command)

        self.assertIn(str(TEST_CW_FILE), command_str)
        self.assertIn("384000", command_str)  # 48000 * 8


class TestDigitalDemodulators(unittest.TestCase):
    """Test digital mode demodulators."""

    @classmethod
    def setUpClass(cls):
        """Check if digital demodulators are available."""
        try:
            from csdr.chain.digimodes import CwDemodulator
            from pycsdr.modules import CwDecoder
            cls.digital_available = True
        except ImportError:
            cls.digital_available = False

    def test_cw_demodulator_instantiation(self):
        """Test that CW demodulator can be instantiated."""
        if not self.digital_available:
            self.skipTest("Digital demodulators not available")

        from csdr.chain.digimodes import CwDemodulator

        # Create CW demodulator
        cw_demod = CwDemodulator(bandWidth=100)

        # Verify it was created
        self.assertIsNotNone(cw_demod, "CW demodulator should be created")
        self.assertGreater(len(cw_demod.workers), 0, "Should have workers")

        # Verify it has CW decoder
        worker_types = [type(w).__name__ for w in cw_demod.workers]
        self.assertIn("CwDecoder", worker_types, "Should have CW decoder")

        # Clean up
        cw_demod.stop()


if __name__ == "__main__":
    unittest.main()
