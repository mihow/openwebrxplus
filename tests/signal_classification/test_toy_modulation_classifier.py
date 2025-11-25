"""
Toy unit test that demonstrates the end-to-end flow:
  IQ samples -> simple features -> tiny PyTorch model (loaded from toy weights) -> predicted label

This test is deterministic (fixed seed), requires numpy and torch, and is intended
as a fast smoke test to validate the plugin integration pipeline.

To run:
  - ensure you have Python with numpy and torch installed
  - run: pytest tests/signal_classification/test_toy_modulation_classifier.py

Notes:
  - The test normalizes features by reference values derived from the AM and FM examples,
    so scaling is deterministic and independent of absolute signal length.
  - The model is a single Linear layer whose weights are defined in the toy_pretrained_weights module.
"""

import numpy as np
from openwebrxplus.signal_classification import inference

RNG = np.random.RandomState(1234)


def synthesize_am(fs, duration, amp=1.0, mod_freq=5.0, mod_depth=0.8):
    t = np.arange(int(fs * duration)) / fs
    envelope = 1.0 + mod_depth * np.cos(2 * np.pi * mod_freq * t)
    phase = 0.01 * np.sin(2 * np.pi * 0.1 * t)
    iq = amp * envelope * np.exp(1j * phase)
    return iq


def synthesize_fm(fs, duration, dev=50.0, mod_freq=2.0):
    t = np.arange(int(fs * duration)) / fs
    inst_freq = dev * np.sin(2 * np.pi * mod_freq * t)
    phase = 2 * np.pi * np.cumsum(inst_freq) / fs
    iq = np.exp(1j * phase)
    return iq


def synthesize_cw(fs, duration, tone_freq=100.0):
    t = np.arange(int(fs * duration)) / fs
    iq = np.exp(1j * 2 * np.pi * tone_freq * t)
    return iq


def synthesize_ssb_like(fs, duration, mod_freq=3.0, mod_depth=0.5):
    t = np.arange(int(fs * duration)) / fs
    phase = 0.5 * np.sin(2 * np.pi * mod_freq * t)
    iq = (1.0 + 0.05 * np.cos(2 * np.pi * 0.5 * t)) * np.exp(1j * phase)
    return iq


def test_toy_modulation_classifier():
    fs = 8000
    duration = 1.0

    cases = [
        ("AM", synthesize_am(fs, duration, amp=1.0, mod_freq=5.0, mod_depth=0.8)),
        ("FM", synthesize_fm(fs, duration, dev=50.0, mod_freq=2.0)),
        ("CW", synthesize_cw(fs, duration, tone_freq=100.0)),
        ("SSB", synthesize_ssb_like(fs, duration, mod_freq=3.0, mod_depth=0.5)),
    ]

    for expected_label, iq in cases:
        pred_label, logits = inference.predict_label_from_iq(iq, fs)
        msg = f"expected={expected_label} pred={pred_label} logits={logits.tolist()}"
        assert pred_label == expected_label, msg
