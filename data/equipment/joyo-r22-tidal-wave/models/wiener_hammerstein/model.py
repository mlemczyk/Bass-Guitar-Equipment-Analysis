"""
Joyo R-22 Tidal Wave: drive path as a phase-aware Wiener-Hammerstein model,
plus the measured dry leg and Blend 12:00 crossfade.

    from model import TidalWave
    tw = TidalWave.load()
    y = tw.apply(x, drive="9:00", blend="max")      # x at SEND scale, 44.1kHz

STRUCTURE (measured, not assumed):

    wet  = H2 * f( k_drive * G * H1 * x )
    dry  = Hdry * x
    out  = wet                         Blend max
         = a * dry + b * wet(t - tau)  Blend 12:00 (a, b, tau calibrated on TW02)
         = dry                         Blend min

  H1    1st-order highpass (fh ~74Hz) x 1st-order lowpass, causal
  f     asymmetric soft clipper: ceiling 1 on the positive half-cycle and r on
        the negative, knee exponents pp / pn, an input bias (DC removed) and a
        linear leak
  k     Drive as a pure pre-clipper gain. The measured taper (dB relative to
        9:00) is: 7:00 -5.8, 9:00 0, 11:00 +6.6, 1:00 +12.9, max +29.2.
        Across 40Hz-2kHz it is flat to 0.16dB at every position
  H2    complex post-clipper response: the cab sim (a deep notch near 1kHz, a
        bottom-octave rolloff) plus the tone stack at its settled positions
        and the re-amp loop's return path
  Hdry  the Blend-min leg: a gentle rising tilt, plus the loop

SCALES. Input `x` is at SEND scale: the source project played probes so that
a -23dBFS peak matched the bass's own level at the pedalboard input. Output is
at the capture (mixer) scale, so it includes the loop's own ~+9dB of gain and
its response. Divide by the bypass loop (`interface/`) for the pedal alone.

TONE STACK: fixed at the settled positions (Presence, Treble, Middle @500Hz,
Bass @40Hz and Level at 12:00). Each control's measured response is in
`../../measurements/` (TW10-TW27) and composes after the blend: the stack is
post-blend (TW28).

Accuracy (source project, fits/tidalwave_twopath_complex_par4.npz, single
path): absolute ladder error 1.7-3.5dB per take at Blend max, 2.2 / 2.6dB on
held-out Drive 11:00 / 1:00, 0.45-2.7dB on held-out Blend 12:00 ladders.
Harmonic levels are NOT modelled well (13dB or worse). Use it for level and
frequency response, not for distortion spectra.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import signal

SR = 44100
NSEG = 16384
FREQ = np.fft.rfftfreq(NSEG, 1 / SR)
DRIVE_TAPER_DB = {"7:00": -5.772742250225127, "9:00": 0.0, "11:00": 6.6412033802092605,
                  "1:00": 12.90757561960808, "max": 29.221515029479917}


def _f(u, r, pp, pn):
    pos = u >= 0
    out = np.empty_like(u)
    up = u[pos]
    out[pos] = up / (1.0 + np.abs(up) ** pp) ** (1.0 / pp)
    un = u[~pos]
    out[~pos] = un / (1.0 + np.abs(un / r) ** pn) ** (1.0 / pn)
    return out


def shaper(u, P):
    b = P["bias"]
    return (_f(u + b, P["r"], P["pp"], P["pn"])
            - _f(np.array([b]), P["r"], P["pp"], P["pn"])[0] + P["leak"] * u)


def h1_filter(x, fh, fl, sr=SR):
    b1, a1 = signal.bilinear([1.0, 0.0], [1.0, 2 * np.pi * fh], sr)
    b2, a2 = signal.bilinear([2 * np.pi * fl], [1.0, 2 * np.pi * fl], sr)
    return signal.lfilter(b2, a2, signal.lfilter(b1, a1, x))


def apply_filter(x, H):
    """Per-bin complex response on the NSEG grid, as a centred FIR."""
    Hb = H.copy()
    Hb[(FREQ < 15.0) | (FREQ > 19000.0)] = 0.0
    h = np.roll(np.fft.irfft(Hb, NSEG), NSEG // 2)
    y = signal.oaconvolve(x, h)
    return y[NSEG // 2:NSEG // 2 + len(x)]


def frac_delay(y, tau):
    n = len(y)
    m = 1 << int(np.ceil(np.log2(n + 64)))
    Y = np.fft.rfft(y, m) * np.exp(-2j * np.pi * np.fft.rfftfreq(m) * tau)
    return np.fft.irfft(Y, m)[:n]


class TidalWave:
    def __init__(self, P, H2, Hdry, blend_cal):
        self.P, self.H2, self.Hdry, self.blend_cal = P, H2, Hdry, blend_cal

    @classmethod
    def load(cls, folder=None):
        d = Path(folder) if folder else Path(__file__).resolve().parent
        meta = json.loads((d / "params.json").read_text(encoding="utf-8"))
        z = np.load(d / "responses.npz")
        return cls(meta["shaper"], z["H2"], z["Hdry"], meta["blend_1200"])

    def wet(self, x, drive="9:00"):
        k = 10 ** (DRIVE_TAPER_DB[drive] / 20.0)
        P = self.P
        z = shaper(P["G"] * k * h1_filter(np.asarray(x, float), P["fh"], P["fl"]), P)
        return apply_filter(z, self.H2)

    def dry(self, x):
        return apply_filter(np.asarray(x, float), self.Hdry)

    def apply(self, x, drive="9:00", blend="max"):
        if blend == "max":
            return self.wet(x, drive)
        if blend == "min":
            return self.dry(x)
        if blend == "12:00":
            c = self.blend_cal
            return c["a"] * self.dry(x) + c["b"] * frac_delay(self.wet(x, drive), c["tau"])
        raise ValueError("blend: 'max', '12:00' or 'min' (the only calibrated positions)")
