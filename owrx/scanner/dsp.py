"""Consolidated DSP functions for the scanner.

Channel extraction, FM/AM demodulation, and WAV output.
Used by scripts/scan_iq.py and available for other scanner components.
"""

import wave

import numpy as np
from scipy.signal import decimate as scipy_decimate, lfilter


def extract_channel(iq, center_freq, signal_freq, sample_rate, channel_bw,
                    target_rate=None):
    """Frequency-shift and decimate to extract a single channel.

    If target_rate is given, choose decimation to produce a rate as close
    to target_rate as possible (must evenly divide sample_rate).

    Returns (channel_iq, actual_rate).
    """
    offset = signal_freq - center_freq
    t = np.arange(len(iq)) / sample_rate
    shifted = iq * np.exp(-1j * 2 * np.pi * offset * t)
    if target_rate and target_rate < sample_rate:
        # Pick decimation that produces closest rate >= target
        decimation = max(1, round(sample_rate / target_rate))
    else:
        decimation = max(1, int(sample_rate / channel_bw))
    dec_i = scipy_decimate(shifted.real, decimation)
    dec_q = scipy_decimate(shifted.imag, decimation)
    actual_rate = sample_rate / decimation
    return dec_i + 1j * dec_q, int(round(actual_rate))


def demod_fm(iq, sample_rate, deviation=5000):
    """FM demodulate with de-emphasis, DC removal, and normalization."""
    phase = np.angle(iq)
    dphase = np.diff(np.unwrap(phase))
    audio = dphase / (2 * np.pi * deviation / sample_rate)
    audio = np.clip(audio, -1.0, 1.0)
    # De-emphasis (75us for Americas)
    tau = 75e-6
    dt = 1.0 / sample_rate
    alpha = dt / (tau + dt)
    audio = lfilter([alpha], [1, -(1 - alpha)], audio)
    # Remove DC offset
    audio = audio - np.mean(audio)
    mx = np.max(np.abs(audio))
    if mx > 0:
        audio = audio / mx * 0.9
    return audio


def demod_am(iq):
    """AM envelope detection with DC removal and normalization."""
    envelope = np.abs(iq)
    audio = envelope - np.mean(envelope)
    # Remove DC offset
    audio = audio - np.mean(audio)
    mx = np.max(np.abs(audio))
    if mx > 0:
        audio = audio / mx * 0.9
    return audio


def save_wav(filename, audio, sample_rate):
    """Save float audio as 16-bit mono WAV."""
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(filename, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
