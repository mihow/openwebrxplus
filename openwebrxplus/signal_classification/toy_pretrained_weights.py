# Toy "pretrained" weights for the unit test.
# This module contains:
#  - labels: list of class names in order
#  - W: weight matrix shape (4,3) following PyTorch nn.Linear convention (out_features x in_features)
#  - b: bias vector shape (4,)
#
# The weights are handcrafted so the minimal linear model distinguishes
# the toy features computed in the test.

import numpy as np

labels = ["AM", "FM", "CW", "SSB"]

# Shape (4, 3): rows = classes, cols = features [env_var, inst_freq_var, spec_peak_ratio]
# Feature ranges (normalized): AM=[1,0,6], FM=[0,1,0.4], CW=[0,0,11], SSB=[0.004,0.001,6]
# The goal is:
#   - AM: high env_var -> AM wins
#   - FM: high inst_freq_var -> FM wins
#   - CW: very high spec_peak_ratio (>10), zero env_var and inst_freq_var -> CW wins
#   - SSB: medium spec_peak_ratio (~6), tiny env_var and inst_freq_var -> SSB wins
W = np.array([
    [15.0, -5.0, -1.0],   # AM: strong positive on env_var
    [-5.0, 20.0, -3.0],   # FM: strong positive on inst_freq_var
    [-10.0, -10.0, 0.8],  # CW: positive on spec_peak_ratio, heavily penalizes any env/freq variance
    [5.0, 5.0, 0.2],      # SSB: positive on small env_var and inst_freq_var
], dtype=np.float32)

# Add biases: CW needs high spec_peak_ratio (>8) to win
b = np.array([0.0, 0.0, -6.0, 0.0], dtype=np.float32)
