"""
Behringer NR300: broadband downward expander with hysteresis, hold and
one-pole ballistics, on 5ms frames.

    from model import load_params, apply_model
    p = load_params()                       # settled: Threshold 9:00, Decay 7:00
    y = apply_model(x, p, sr=44100, key=k)  # x, key: float arrays at the capture scale

    detector   L = level of the KEY signal per frame, dB
               "rms":  one-pole mean of power over det_ms
               "peak": peak-hold, det_ms release
    target     clip(slope * (L - T), floor, 0);  T = thr, or thr - hyst while open
    ballistics attack_ms while opening; while closing, wait hold_ms, then release_ms
    output     x * 10^((gain + makeup)/20), polarity inverted (measured)

LEVELS ARE ABSOLUTE. `thr` is in dBFS at the measurement capture, where the
bass played normally peaks at -14.0dBFS and averages -33.2dBFS RMS (the R03
performance re-amped). Scale your key to that, or pass `det_offset_db` =
(-14.0 - your playing peak in dBFS).

THE KEY. The NR300 is wired as a 4-cable loop: it detects on the bass before
the loop and gates the loop's return. In every NR take the loop was empty, so
key == input. To simulate it in a chain, pass the pre-loop signal as `key`.

Broadband is measured: frames gated by 12dB+ show a -16dB +-2 coherent transfer
from 20Hz to 4kHz, and partly gated frames are flat to 0.6dB.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FRAME_MS = 5.0

try:
    from numba import njit
except ImportError:                     # pure python fallback, ~100x slower
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]


@njit(cache=True)
def _gate_gain(L, peak, thr, hyst, floor, slope, det, atk, rel, hold, frame_ms):
    n = L.shape[0]
    out = np.empty(n)
    a_d = np.exp(-frame_ms / max(det, 1e-3))
    a_a = np.exp(-frame_ms / max(atk, 1e-3))
    a_r = np.exp(-frame_ms / max(rel, 1e-3))
    hold_frames = hold / frame_ms
    pw = 10.0 ** (L[0] / 10.0)
    g = 0.0
    below = 0.0
    for i in range(n):
        p_i = 10.0 ** (L[i] / 10.0)
        if peak:
            pw = max(p_i, a_d * pw)
        else:
            pw = a_d * pw + (1.0 - a_d) * p_i
        ld = 10.0 * np.log10(pw + 1e-20)
        t_eff = thr - hyst if g > -3.0 else thr
        target = slope * (ld - t_eff)
        if target > 0.0:
            target = 0.0
        if target < floor:
            target = floor
        if target >= g:
            below = 0.0
            g = a_a * g + (1.0 - a_a) * target
        else:
            below += 1.0
            if below > hold_frames:
                g = a_r * g + (1.0 - a_r) * target
        out[i] = g
    return out


def gain_db(det_frames, p, frame_ms=FRAME_MS):
    """Per-frame gain (dB) from per-frame detector levels (dB)."""
    d = np.ascontiguousarray(np.asarray(det_frames, dtype=np.float64)
                             + p.get("det_offset_db", 0.0))
    return _gate_gain(d, p["detector"] == "peak", p["thr"], p["hyst"], p["floor"],
                      p["slope"], p["det_ms"], p["attack_ms"], p["release_ms"],
                      p["hold_ms"], frame_ms) + p["makeup"]


def _frames(x, n, peak):
    m = len(x) // n * n
    fr = np.asarray(x[:m]).reshape(-1, n)
    if peak:
        return 20 * np.log10(np.abs(fr).max(axis=1) + 1e-10) - 3.01
    return 10 * np.log10((fr ** 2).mean(axis=1) + 1e-20)


def apply_model(x, p, sr=44100, key=None, invert=True):
    """Gate audio. float in, float out, same length; gain interpolated per sample."""
    x = np.asarray(x, dtype=np.float64)
    k = x if key is None else np.asarray(key, dtype=np.float64)
    n = int(sr * FRAME_MS / 1000.0)
    g = gain_db(_frames(k, n, p["detector"] == "peak"), p)
    centres = (np.arange(len(g)) + 0.5) * n
    y = x * 10 ** (np.interp(np.arange(len(x)), centres, g) / 20.0)
    return -y if invert else y


def load_params(take="NR02", path=None):
    """Parameters for one measured setting (NR02 = settled)."""
    p = Path(path) if path else Path(__file__).with_name("params.json")
    return json.loads(p.read_text(encoding="utf-8"))["per_take"][take]["params"]
