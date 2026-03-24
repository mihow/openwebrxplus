"""Unit tests for owrx.scanner.dsp functions."""

import os
import tempfile
import unittest
import wave

import numpy as np


class TestExtractChannel(unittest.TestCase):
    """Test extract_channel with synthetic tones."""

    def test_extract_channel_shifts_tone_to_baseband(self):
        """A tone offset from center should end up near DC after extraction."""
        from owrx.scanner.dsp import extract_channel

        sample_rate = 2_400_000
        center_freq = 100_000_000
        signal_freq = 100_050_000  # 50 kHz offset
        channel_bw = 16_000
        duration = 0.01  # 10 ms
        n_samples = int(sample_rate * duration)

        # Generate a tone at signal_freq
        t = np.arange(n_samples) / sample_rate
        offset = signal_freq - center_freq
        iq = np.exp(1j * 2 * np.pi * offset * t).astype(np.complex64)

        ch_iq, actual_rate = extract_channel(
            iq, center_freq, signal_freq, sample_rate, channel_bw
        )

        self.assertGreater(len(ch_iq), 0)
        self.assertGreater(actual_rate, 0)
        self.assertLessEqual(actual_rate, sample_rate)
        # After shifting, the channel IQ should have most energy near DC
        # (i.e., the phase should be roughly constant)
        phase_diff = np.abs(np.diff(np.angle(ch_iq)))
        # Wrap to [-pi, pi]
        phase_diff = np.abs((phase_diff + np.pi) % (2 * np.pi) - np.pi)
        mean_phase_change = np.mean(phase_diff)
        self.assertLess(mean_phase_change, 0.5,
                        "Tone should be near DC after channel extraction")

    def test_extract_channel_with_target_rate(self):
        """target_rate should control the output sample rate."""
        from owrx.scanner.dsp import extract_channel

        sample_rate = 2_400_000
        n_samples = 24000
        iq = np.ones(n_samples, dtype=np.complex64)

        ch_iq, actual_rate = extract_channel(
            iq, 100e6, 100e6, sample_rate, 16000, target_rate=48000
        )

        self.assertGreater(actual_rate, 0)
        # actual_rate should be close to 48000
        self.assertAlmostEqual(actual_rate, 48000, delta=10000)


class TestDemodFM(unittest.TestCase):
    """Test FM demodulation."""

    def test_demod_fm_produces_nonzero_audio(self):
        """FM demod of a frequency-modulated signal should produce audio."""
        from owrx.scanner.dsp import demod_fm

        sample_rate = 48000
        duration = 0.1
        n_samples = int(sample_rate * duration)
        t = np.arange(n_samples) / sample_rate

        # Create FM-modulated signal: carrier with 1 kHz modulation
        mod_freq = 1000
        deviation = 5000
        phase = 2 * np.pi * (deviation / mod_freq) * np.sin(2 * np.pi * mod_freq * t)
        iq = np.exp(1j * phase).astype(np.complex64)

        audio = demod_fm(iq, sample_rate, deviation=deviation)

        self.assertGreater(len(audio), 0)
        self.assertGreater(np.max(np.abs(audio)), 0.01,
                          "FM demod should produce non-zero audio")

    def test_demod_fm_silent_carrier(self):
        """FM demod of an unmodulated carrier should produce near-silence."""
        from owrx.scanner.dsp import demod_fm

        sample_rate = 48000
        n_samples = 4800
        # Pure carrier (no frequency modulation)
        iq = np.ones(n_samples, dtype=np.complex64)

        audio = demod_fm(iq, sample_rate, deviation=5000)
        rms = np.sqrt(np.mean(audio ** 2))
        self.assertLess(rms, 0.1, "Unmodulated carrier should produce near-silence")


class TestDemodAM(unittest.TestCase):
    """Test AM demodulation."""

    def test_demod_am_produces_nonzero_audio(self):
        """AM demod of an amplitude-modulated signal should produce audio."""
        from owrx.scanner.dsp import demod_am

        sample_rate = 48000
        duration = 0.1
        n_samples = int(sample_rate * duration)
        t = np.arange(n_samples) / sample_rate

        # AM signal: carrier with 1 kHz tone, 50% modulation depth
        mod_freq = 1000
        envelope = 1.0 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
        iq = (envelope * np.exp(1j * 2 * np.pi * 10000 * t)).astype(np.complex64)

        audio = demod_am(iq)

        self.assertGreater(len(audio), 0)
        self.assertGreater(np.max(np.abs(audio)), 0.01,
                          "AM demod should produce non-zero audio")

    def test_demod_am_constant_envelope(self):
        """AM demod of a constant-envelope signal should produce near-silence."""
        from owrx.scanner.dsp import demod_am

        n_samples = 4800
        iq = np.ones(n_samples, dtype=np.complex64)

        audio = demod_am(iq)
        rms = np.sqrt(np.mean(audio ** 2))
        self.assertLess(rms, 0.01,
                       "Constant envelope should produce near-silence")


class TestSaveWav(unittest.TestCase):
    """Test WAV file output."""

    def test_save_wav_creates_valid_file(self):
        """save_wav should create a readable 16-bit mono WAV."""
        from owrx.scanner.dsp import save_wav

        sample_rate = 16000
        duration = 0.5
        n_samples = int(sample_rate * duration)
        audio = np.sin(2 * np.pi * 440 * np.arange(n_samples) / sample_rate)
        audio = audio * 0.9  # keep within [-1, 1]

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name

        try:
            save_wav(wav_path, audio, sample_rate)

            self.assertTrue(os.path.exists(wav_path))
            self.assertGreater(os.path.getsize(wav_path), 100)

            # Verify WAV metadata
            with wave.open(wav_path, 'r') as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getsampwidth(), 2)
                self.assertEqual(wf.getframerate(), sample_rate)
                self.assertEqual(wf.getnframes(), n_samples)
        finally:
            os.unlink(wav_path)

    def test_save_wav_empty_audio(self):
        """save_wav with empty audio should create a valid (empty) WAV."""
        from owrx.scanner.dsp import save_wav

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            wav_path = f.name

        try:
            save_wav(wav_path, np.array([]), 16000)
            self.assertTrue(os.path.exists(wav_path))
            with wave.open(wav_path, 'r') as wf:
                self.assertEqual(wf.getnframes(), 0)
        finally:
            os.unlink(wav_path)


if __name__ == "__main__":
    unittest.main()
