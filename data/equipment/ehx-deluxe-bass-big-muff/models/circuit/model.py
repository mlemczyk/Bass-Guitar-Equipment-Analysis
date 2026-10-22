"""
EHX Deluxe Bass Big Muff: a circuit model (Black Russian core), fitted.

    from model import BigMuff
    m = BigMuff.load()
    y = m.apply(x, sustain="12:00", tone="max", blend="12:00")   # x at capture scale, 44.1kHz

`muff_circuit.py` (beside this file) simulates the fuzz core as a circuit:
four 2N5088 stages, 1N914 clippers, the Big Muff tone stack, and Sustain and
Tone as real pots. It is a DK-method nodal solver (13 states, 10 Newton
ports, Ebers-Moll), 2x oversampled, with numba required. This wrapper adds
what the fit found, and the Deluxe's parts the circuit leaves out:

  * the fitted part values: coupling caps x1.36, tone-stack caps x0.79
    (treble) and x0.48 (bass), beta ~550, diode n 2.04, Sustain taper 12% at
    half rotation (params.json `theta`)
  * input scale `k_in` (volts per digital unit) and output gain (dB), both fitted
  * Blend as a crossfade against a FLAT dry path. Wet fractions measured at
    playing level: min 0, 9:00 0.05, 12:00 0.445, 3:00 0.875, max 1.0
  * the crossover is out, and the gate is open (9:00 or below)

SCALE. `x` is the signal as it reaches the pedal, expressed as the capture of
the pedal at Blend min (MUFF14): the re-amp loop and the Deluxe's flat dry path
are lumped in, and normal playing peaks near -14dBFS. Output is at the same
scale as the Blend-max captures.

Accuracy: probe fit 2.09dB (ladder rungs -50..-20dBFS, 1/6 octave,
40Hz-6kHz, plus 110Hz harmonics). Held-out knob settings 0.87-1.85dB on the
ladder. Played-performance re-amps, never fitted: 0.69dB (settled), 1.08dB
(Tone max, Blend max), 1.39dB (Tone min, Blend max), as RMS over five
descriptors (four spectral bands and a THD ratio). See validation.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import muff_circuit as mc

BLEND = {"min": 0.0, "9:00": 0.05, "12:00": 0.445, "3:00": 0.875, "max": 1.0}


class BigMuff:
    def __init__(self, theta, out_gain_db):
        self.theta, self.out_gain = theta, 10 ** (out_gain_db / 20.0)

    @classmethod
    def load(cls, path=None):
        p = Path(path) if path else Path(__file__).with_name("params.json")
        d = json.loads(p.read_text(encoding="utf-8"))
        return cls(d["theta"], d["out_gain_db"])

    def settings(self, sustain, tone):
        t = self.theta
        return (mc.Settings(sustain=mc.clock_to_travel(sustain), tone=mc.clock_to_travel(tone),
                            sustain_mid=t["sustain_mid"],
                            cap_scale={g: 2.0 ** t[f"cap_{g}"] for g in mc.CAP_GROUPS},
                            bjt=dict(mc.BJT, bf=10 ** t["log10_beta"]),
                            diode=dict(mc.DIODE, n=t["diode_n"])),
                10 ** t["log10_k_in"])

    def wet(self, x, sr=44100, sustain="12:00", tone="max"):
        s, k_in = self.settings(sustain, tone)
        return mc.simulate(np.asarray(x, float), sr, s, k_in, oversample=2) * self.out_gain

    def apply(self, x, sr=44100, sustain="12:00", tone="max", blend="12:00"):
        b = BLEND[blend] if isinstance(blend, str) else float(blend)
        x = np.asarray(x, float)
        if b == 0.0:
            return x.copy()
        return (1.0 - b) * x + b * self.wet(x, sr, sustain, tone)
