"""
Frame envelopes and sample alignment, for level-acting stages (gates,
compressors) measured against a re-amp of real playing.

A gate acts on level, not frequency, so its measurement is a pair of frame
envelopes: what went in and what came out, frame by frame. Those envelopes are
published (as int16 centi-dB) even where the audio they came from is not.
"""

from __future__ import annotations

import numpy as np
from scipy import signal

FRAME_MS = 5.0


def frame_len(sr, frame_ms=FRAME_MS):
    return int(sr * frame_ms / 1000.0)


def align(a, b, m=400000):
    """Sample-align b to a by FFT cross-correlation. Returns (a, b, lag, polarity)."""
    m = min(m, len(a), len(b))
    c = signal.fftconvolve(b[:m] - b[:m].mean(), (a[:m] - a[:m].mean())[::-1], "full")
    k = int(np.argmax(np.abs(c)))
    lag, pol = k - (m - 1), float(np.sign(c[k]))
    if lag > 0:
        b = b[lag:]
    elif lag < 0:
        a = a[-lag:]
    n = min(len(a), len(b))
    return a[:n], b[:n], lag, pol


def env_db(x, n):
    """Frame RMS, dB."""
    m = len(x) // n * n
    return 10 * np.log10((np.asarray(x[:m]).reshape(-1, n) ** 2).mean(axis=1) + 1e-20)


def peak_db(x, n):
    """Frame peak, dB, minus 3.01 so a sine reads the same as env_db."""
    m = len(x) // n * n
    return 20 * np.log10(np.abs(np.asarray(x[:m]).reshape(-1, n)).max(axis=1) + 1e-10) - 3.01


def to_cdb(db):
    return np.clip(np.round(np.asarray(db) * 100), -32768, 32767).astype(np.int16)


def from_cdb(c):
    return np.asarray(c, dtype=np.float64) / 100.0
