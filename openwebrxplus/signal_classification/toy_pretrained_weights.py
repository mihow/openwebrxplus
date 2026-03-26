"""
Toy pretrained weights for signal modulation classification.

This module contains a small label list and explicitly specified numpy arrays
for weight matrix (W) and bias (b) for a tiny PyTorch classifier. The model
is a single Linear layer (input size 3, output size 4) with handcrafted weights
designed to classify synthetic modulation types based on simple features.

Features expected (input size 3):
    0: envelope_variance - scaled variance of signal envelope
    1: inst_freq_variance - scaled variance of instantaneous frequency
    2: log_spectral_peak_ratio - log of spectral peak ratio, normalized

Labels (output size 4):
    0: AM  - Amplitude Modulation
    1: FM  - Frequency Modulation
    2: CW  - Continuous Wave
    3: SSB - Single Sideband

Feature characteristics for each modulation type:
    AM:  High envelope variance, near-zero inst_freq variance
    FM:  Zero envelope variance, moderate inst_freq variance
    CW:  Zero envelope/inst_freq variance, very high spectral peak
    SSB: Low envelope variance, high inst_freq variance, low spectral peak
"""

import numpy as np

# Labels corresponding to model output indices
LABELS = ["AM", "FM", "CW", "SSB"]

# Weight matrix: shape (4, 3) - maps 3 input features to 4 output classes
# Rows correspond to output classes (AM, FM, CW, SSB)
# Columns correspond to input features (envelope_var, inst_freq_var, log_peak_ratio)
#
# These weights are designed to properly classify synthetic signals with the
# following scaled feature ranges:
#   - envelope_var: ~0 (FM/CW/SSB) to ~1 (AM)
#   - inst_freq_var: ~0 (AM/CW) to ~0.9 (FM) to ~1.3 (SSB)
#   - log_peak_ratio: ~-0.9 (SSB) to ~1 (CW)
W = np.array(
    [
        [4.0, -0.5, 0.5],   # AM: high weight on envelope_var
        [0.0, 3.0, 0.0],    # FM: moderate inst_freq_var
        [-1.5, -1.5, 3.5],  # CW: high log_peak_ratio, nothing else
        [-0.5, 4.0, -0.5],  # SSB: highest inst_freq_var
    ],
    dtype=np.float32,
)

# Bias vector: shape (4,)
# Biases are tuned to set appropriate decision thresholds
b = np.array([0.0, -1.5, 0.0, -3.0], dtype=np.float32)
