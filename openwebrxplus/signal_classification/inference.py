"""
Inference helper for toy signal classification prototype.

Functions:
 - compute_features(iq, fs)
 - build_linear_model_from_state(state_dict_path=None, num_classes=4)
 - predict_label_from_iq(iq, fs, state_dict_path=None)

Notes:
 - This is a minimalist prototype: the real plugin will later load TorchSig models.
 - For now we use a single Linear layer. If a state_dict_path is provided and points to a
   compatible state_dict, it will be loaded; otherwise the toy_pretrained_weights module is used.
 - TODO: add TorchScript/ONNX export in CI and a lighter runtime path using onnxruntime.
"""

import os
import numpy as np
import torch
import torch.nn as nn

from . import toy_pretrained_weights


def compute_features(iq, fs):
    """Compute 3 features: envelope variance, instantaneous freq variance, spectral peak ratio."""
    env = np.abs(iq)
    env_var = float(np.var(env))

    phase = np.angle(iq)
    phase_unwrapped = np.unwrap(phase)
    inst_freq = np.diff(phase_unwrapped) * fs / (2 * np.pi)
    inst_freq_var = float(np.var(inst_freq)) if inst_freq.size > 0 else 0.0

    spec = np.abs(np.fft.fft(iq))
    peak = float(np.max(spec))
    mean = float(np.mean(spec)) + 1e-12
    spec_peak_ratio = peak / mean

    return np.array([env_var, inst_freq_var, spec_peak_ratio], dtype=np.float32)


def build_linear_model_from_state(state_dict_path=None, num_classes=4):
    """Build a Linear(3,num_classes) model and load state dict if provided. Fallback to toy weights."""
    model = nn.Linear(3, num_classes, bias=True)

    if state_dict_path and os.path.exists(state_dict_path):
        sd = torch.load(state_dict_path, map_location="cpu", weights_only=True)
        try:
            model.load_state_dict(sd)
            return model
        except Exception:
            # Fall back to toy weights if incompatible
            pass

    # fallback
    model.weight.data = torch.from_numpy(toy_pretrained_weights.W.copy())
    model.bias.data = torch.from_numpy(toy_pretrained_weights.b.copy())
    return model


def predict_label_from_iq(iq, fs, state_dict_path=None, reference_scaler=None):
    """Compute features from IQ, normalize by reference_scaler or by AM/FM reference, run model, return label."""
    feats = compute_features(iq, fs)

    # if no provided scaler, compute a deterministic one using AM and FM references
    if reference_scaler is None:
        # make short AM/FM references
        t = np.arange(int(fs * 0.5)) / fs
        am = (1.0 + 0.8 * np.cos(2 * np.pi * 5.0 * t)).astype(np.complex64)
        phase = np.cumsum(50.0 * np.sin(2 * np.pi * 2.0 * t)) * (2 * np.pi / fs)
        fm = np.exp(1j * phase).astype(np.complex64)
        ref_am = compute_features(am, fs)
        ref_fm = compute_features(fm, fs)
        ref = np.maximum(ref_am, ref_fm)
        ref = np.maximum(ref, 1e-8)
    else:
        ref = np.array(reference_scaler, dtype=np.float32)

    feats_norm = feats / ref

    model = build_linear_model_from_state(state_dict_path)
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(feats_norm.astype(np.float32)).unsqueeze(0)
        logits = model(x).numpy().squeeze()
    pred_idx = int(np.argmax(logits))
    label = toy_pretrained_weights.labels[pred_idx]
    return label, logits
