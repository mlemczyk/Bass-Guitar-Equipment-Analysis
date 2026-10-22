"""
Boss BC-1X: two-band compressor model.

    from model import load_params, apply_model
    y = apply_model(x, load_params(), sr=44100)    # x at the capture scale (see below)

FORM. A complementary zero-phase split at ~311Hz (Butterworth 4th order,
low = filtfilt lowpass, high = input - low). Each band has its own compressor:

    detector   hybrid: max(one-pole RMS over detector_ms, peak follower
               (peak_ms release) as a sine-RMS level - peak_offset_db)
    static     soft-knee curve: below thresh - knee/2 no gain change; above
               thresh + knee/2 a slope of (1/ratio - 1); quadratic between
    smoothing  one-pole on the gain, attack_ms when gain falls, release_ms when it rises
    output     band * 10^((gain + makeup)/20), bands summed

Each band's detector hears its own band from a separate 4th-order split
(`detector_order`), so bass fundamentals drive the high band's detector only
weakly. The BC01 two-tone take requires that: an 80Hz tone rising 40dB moved the
upper probe tones by only 0.5-1.0dB.

FITTED: static curves and crossover on the ess_ladder (BC01 vs bypass BC15),
dynamics on a played performance re-amped through both. This is the pedal at
its settled knobs: Threshold, Ratio, Release 12:00, Level 11:00. Other knob
positions are measured (`../../measurements/`) but not modelled.

LEVELS ARE ABSOLUTE: dBFS at the capture, where the bass played normally peaks
at about -14dBFS. Thresholds -39 (low band) and -49dBFS (high band).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import signal

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]


@njit(cache=True)
def _band_gain_hybrid(x, thresh, ratio, knee, rms_c, peak_c, offset, atk, rel):
    n = x.shape[0]
    out = np.empty(n)
    s = 1.0 / ratio - 1.0
    ms = 0.0
    pk = 0.0
    g = 0.0
    for i in range(n):
        a = abs(x[i])
        ms = rms_c * ms + (1.0 - rms_c) * a * a
        pk = a if a > pk else pk * peak_c
        l1 = 10.0 * np.log10(ms + 1e-24)
        l2 = 20.0 * np.log10(pk * 0.7071067811865476 + 1e-12) - offset
        lvl = l1 if l1 > l2 else l2
        over = lvl - thresh
        if over <= -knee / 2:
            t = 0.0
        elif over >= knee / 2:
            t = over * s
        else:
            t = s * (over + knee / 2) ** 2 / (2 * knee)
        c = atk if t < g else rel
        g = c * g + (1.0 - c) * t
        out[i] = g
    return out


def static_gain_db(level_db, thresh, ratio, knee, makeup):
    """The static curve alone (steady sine at `level_db` RMS, one band)."""
    over = np.asarray(level_db, dtype=float) - thresh
    s = 1.0 / ratio - 1.0
    g = np.where(over <= -knee / 2, 0.0,
                 np.where(over >= knee / 2, over * s, s * (over + knee / 2) ** 2 / (2 * knee)))
    return g + makeup


def _coef(ms, sr):
    return float(np.exp(-1.0 / (max(ms, 1e-3) * sr / 1000.0)))


def split(x, fcs, order, sr):
    bands, rest = [], np.asarray(x, dtype=np.float64)
    for fc in fcs:
        sos = signal.butter(order, fc, "lowpass", fs=sr, output="sos")
        lo = signal.sosfiltfilt(sos, rest)
        bands.append(lo)
        rest = rest - lo
    bands.append(rest)
    return bands


def apply_bands(x, p, sr=44100):
    x = np.asarray(x, dtype=np.float64)
    audio = split(x, p["crossovers_hz"], p["split_order"], sr)
    det = split(x, p["crossovers_hz"], p["detector_order"], sr)
    out = []
    for xb, db, bp, tc in zip(audio, det, p["bands"], p["dynamics"]):
        g = _band_gain_hybrid(db, bp["thresh"], bp["ratio"], bp["knee"],
                              _coef(tc["detector_ms"], sr), _coef(p["peak_ms"], sr),
                              p["peak_offset_db"], _coef(tc["attack_ms"], sr),
                              _coef(tc["release_ms"], sr))
        out.append(xb * 10 ** ((g + bp["makeup"]) / 20.0))
    return out


def apply_model(x, p, sr=44100):
    return np.sum(apply_bands(x, p, sr), axis=0)


def load_params(path=None):
    p = Path(path) if path else Path(__file__).with_name("params.json")
    return json.loads(p.read_text(encoding="utf-8"))["params"]
