"""
Donner EQ Seeker: ten-band graphic-EQ model, fitted to measurements.

    from model import SeekerModel
    m = SeekerModel.load()                        # params.json beside this file, default form
    H = m.response(freqs_hz, {"125": -5, "250": -5})
    y = m.apply(x, 44100, {"500": -2, "1k": -2, "2k": -2})
    SeekerModel.load(form="ratio")                # the shared-network form

Accuracy (validation.json), RMS over 40Hz-10kHz: single-band settings 0.5dB;
multi-band combinations 0.9dB fitted, 1.7dB when each combination is left out
of the fit and predicted. Worst: all ten bands at +2 (SEEK17), 2.5dB left out.

TWO FORMS, SAME PARAMETERS, AND THE DATA DOES NOT CHOOSE BETWEEN THEM.
`cascade` (default; marginally better left-out score) treats the bands as
independent filters in series. `ratio` puts every slider in ONE feedback
network, which is how most analogue graphic EQs are built (each slider's
wiper feeds a series-resonant band filter into either the input or the
feedback side of a single op-amp):

            1 + sum_i K_i * u(+n_i) * T_i(s)
    H(s) = ------------------------------------
            1 + sum_i K_i * u(-n_i) * T_i(s)

    T_i(s) = (s / (Q_i w_i)) / (s^2 / w_i^2 + s / (Q_i w_i) + 1)   unity-peak bandpass
    u(n)   = the slider law, n in -5..+5: u(-5) = 0, u(+5) = 1, monotone

A slider at n couples its band filter into the input side with weight u(n)
and into the feedback side with weight u(-n). At n = 0 the two are equal, so
the band is flat, but it still loads the shared network by u(0) on both sides,
and that dilutes every neighbour. The cascade form is the product of the same
single-band sections, so there effects add in dB.

The source project found that combinations do not add in dB, but it tested
that with an ASSUMED slider law. With the law FITTED (`slider_law_by_notch`,
11 values for n = -5..+5, one per form), the independent-band cascade
predicts the combinations as well as the shared-network form. The law is only
identified at the notches that were measured (-5, -4, -3, -2, 0, +2, +5);
values at -1, +1, +3, +4 are interpolation and differ between the forms.

The model is relative to the pedal ENGAGED with every slider at 0. Pass
`vs_bypass=True` to add the measured insertion response (engaged-flat vs
bypassed).

Level slider: `level_gain_db` interpolates the points in params.json (-5 is
a clean measurement; +2..+4 are approximate, from full-chain loudness).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

BANDS = ["31.25", "62.5", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]


@dataclass
class SeekerModel:
    f0: np.ndarray           # band centres, Hz
    q: np.ndarray
    k: np.ndarray
    law: np.ndarray          # u(n) at n = -5..+5 (law[0] = 0, law[10] = 1)
    level_points: dict       # level-slider notch -> dB
    insertion: dict | None = None    # {"f_hz": [...], "db": [...]}

    cascade_default: bool = True

    @classmethod
    def load(cls, path=None, form=None):
        """form: "cascade" or "ratio"; default is params.json's `default_form`."""
        p = Path(path) if path else Path(__file__).with_name("params.json")
        d = json.loads(p.read_text(encoding="utf-8"))
        form = form or d["default_form"]
        fp = d["forms"][form]
        b = fp["bands"]
        return cls(np.array([b[n]["f0_hz"] for n in BANDS]),
                   np.array([b[n]["q"] for n in BANDS]),
                   np.array([b[n]["k"] for n in BANDS]),
                   np.array(fp["slider_law_by_notch"]),
                   {int(k): v for k, v in d["level_slider_db"].items()},
                   d.get("insertion_vs_bypass"),
                   form == "cascade")

    def weights(self, sliders: dict):
        """(input-side, feedback-side) weights per band."""
        n = np.array([float(sliders.get(b, 0)) for b in BANDS])
        grid = np.arange(-5, 6)
        return np.interp(n, grid, self.law), np.interp(-n, grid, self.law)

    def response(self, f_hz, sliders: dict, level: float = 0, cascade=None,
                 vs_bypass=False) -> np.ndarray:
        """Complex response at f_hz. `cascade` defaults to the loaded form."""
        if cascade is None:
            cascade = self.cascade_default
        s = 2j * np.pi * np.asarray(f_hz, dtype=float)[:, None]
        w = 2 * np.pi * self.f0[None, :]
        T = (s / (self.q * w)) / (s * s / (w * w) + s / (self.q * w) + 1)
        a, b = self.weights(sliders)
        num = self.k * a[None, :] * T
        den = self.k * b[None, :] * T
        if cascade:
            H = np.prod((1 + num) / (1 + den), axis=1)
        else:
            H = (1 + num.sum(axis=1)) / (1 + den.sum(axis=1))
        H = H * 10 ** (self.level_gain_db(level) / 20)
        if vs_bypass and self.insertion:
            H = H * 10 ** (np.interp(f_hz, self.insertion["f_hz"], self.insertion["db"]) / 20)
        return H

    def level_gain_db(self, n: float) -> float:
        ks = sorted(self.level_points)
        return float(np.interp(n, ks, [self.level_points[k] for k in ks]))

    def fir(self, sr: int, sliders: dict, level: float = 0, ntaps: int = 16384, **kw):
        """Linear-phase-free FIR: the model's own (minimum-phase) impulse
        response, sampled and truncated with a half-Hann tail."""
        f = np.fft.rfftfreq(ntaps * 4, 1 / sr)
        f[0] = 1e-3
        h = np.fft.irfft(self.response(f, sliders, level, **kw), ntaps * 4)[:ntaps]
        tail = ntaps // 8
        h[-tail:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, tail)))
        return h

    def apply(self, x, sr: int, sliders: dict, level: float = 0, **kw):
        from scipy.signal import oaconvolve
        return oaconvolve(np.asarray(x, dtype=float), self.fir(sr, sliders, level, **kw))[:len(x)]
