"""Micro-RNN forward kernel — BA Step 2

Branchless activations + batch forward inference (N,16)->(N,7).
Numpy path is vectorized; pure-python fallback keeps prod running when numpy absent.
Genome layout: 295 float32 = W1(16*12)=192 + b1(12)=12 =>204, + W2(12*7)=84 + b2(7)=7 =>91.
"""

from __future__ import annotations

import math

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    HAS_NUMPY = False


# --- activations -------------------------------------------------------

def fast_tanh(x):
    if HAS_NUMPY:
        # x / (1+|x|) — branchless, no exp
        # handle ndarray and scalar
        return x / (1.0 + np.abs(x))
    # scalar / list fallback
    if isinstance(x, list):
        return [v / (1.0 + abs(v)) for v in x]
    return x / (1.0 + abs(x))


def fast_sigmoid(x):
    if HAS_NUMPY:
        return 0.5 * (fast_tanh(0.5 * x) + 1.0)
    if isinstance(x, list):
        return [0.5 * (v / (1.0 + abs(v)) + 1.0) for v in [0.5 * v for v in x]]
    # scalar: 0.5*(tanh(0.5x)+1)
    t = (0.5 * x) / (1.0 + abs(0.5 * x))
    return 0.5 * (t + 1.0)


def leaky_relu(x, alpha: float = 0.01):
    if HAS_NUMPY:
        return np.where(x > 0, x, x * alpha)
    if isinstance(x, list):
        return [v if v > 0 else v * alpha for v in x]
    return x if x > 0 else x * alpha


# --- forward -----------------------------------------------------------

def forward_batch(inputs, genomes, hidden_state=None):
    """Batch forward: inputs (N,16), genomes (N,295) -> outputs (N,7), new_hidden (N,1).

    Updates hidden_state in-place if provided.
    Uses numpy einsum when available, else pure python loops.
    """
    if HAS_NUMPY:
        return _forward_numpy(inputs, genomes, hidden_state)
    return _forward_pure(inputs, genomes, hidden_state)


def _forward_numpy(inputs, genomes, hidden_state):
    N = inputs.shape[0]
    # unpack genomes
    # genomes: (N,295). First 204 = W1+b1, next 91 = W2+b2.
    # W1 shape (16,12), b1 (12) -> need (N,16,12) and (N,12)
    W1 = genomes[:, 0:192].reshape(N, 16, 12)
    b1 = genomes[:, 192:204]  # (N,12)
    W2 = genomes[:, 204:288].reshape(N, 12, 7)
    b2 = genomes[:, 288:295]  # (N,7)

    # H = leaky_relu( einsum('bi,bij->bj', X, W1) + b1 )
    # einsum per batch: (N,1,16) @ (N,16,12) -> (N,12)
    H = np.einsum("bi,bij->bj", inputs, W1) + b1
    H = np.where(H > 0, H, H * 0.01)

    Y = np.einsum("bi,bij->bj", H, W2) + b2  # (N,7)

    # per-output activations
    out = np.empty_like(Y)
    out[:, 0] = 0.5 * ((0.5 * Y[:, 0]) / (1.0 + np.abs(0.5 * Y[:, 0])) + 1.0)  # fast_sigmoid thrust
    out[:, 1] = Y[:, 1] / (1.0 + np.abs(Y[:, 1]))  # fast_tanh steer
    out[:, 2] = Y[:, 2] / (1.0 + np.abs(Y[:, 2]))
    out[:, 3] = Y[:, 3] / (1.0 + np.abs(Y[:, 3]))
    out[:, 4] = 0.5 * ((0.5 * Y[:, 4]) / (1.0 + np.abs(0.5 * Y[:, 4])) + 1.0)  # vocal_amp
    out[:, 5] = Y[:, 5] / (1.0 + np.abs(Y[:, 5]))
    out[:, 6] = Y[:, 6] / (1.0 + np.abs(Y[:, 6]))

    if hidden_state is not None:
        hidden_state[:, 0] = out[:, 6]

    return out, hidden_state


def _forward_pure(inputs, genomes, hidden_state):
    # inputs: list of lists or 2D
    # genomes: list of lists
    N = len(inputs)
    out = []
    for n in range(N):
        x = inputs[n]  # len 16
        g = genomes[n]  # len 295
        # unpack
        W1_flat = g[0:192]
        b1 = g[192:204]
        W2_flat = g[204:288]
        b2 = g[288:295]
        # W1 shape (16,12) row-major: index i*12 + j
        H = [0.0] * 12
        for j in range(12):
            s = b1[j]
            for i in range(16):
                s += x[i] * W1_flat[i * 12 + j]
            H[j] = s if s > 0 else s * 0.01
        Y = [0.0] * 7
        for k in range(7):
            s = b2[k]
            for j in range(12):
                s += H[j] * W2_flat[j * 7 + k]
            Y[k] = s
        # activations
        # fast ops
        Y0 = 0.5 * ( (0.5 * Y[0]) / (1.0 + abs(0.5 * Y[0])) + 1.0 )
        Y1 = Y[1] / (1.0 + abs(Y[1]))
        Y2 = Y[2] / (1.0 + abs(Y[2]))
        Y3 = Y[3] / (1.0 + abs(Y[3]))
        Y4 = 0.5 * ( (0.5 * Y[4]) / (1.0 + abs(0.5 * Y[4])) + 1.0 )
        Y5 = Y[5] / (1.0 + abs(Y[5]))
        Y6 = Y[6] / (1.0 + abs(Y[6]))
        out.append([Y0, Y1, Y2, Y3, Y4, Y5, Y6])
        if hidden_state is not None:
            hidden_state[n][0] = Y6
    return out, hidden_state
