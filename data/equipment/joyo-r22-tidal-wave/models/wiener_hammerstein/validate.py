#!/usr/bin/env python3
"""
Check the port: play the ess_ladder probe (sent at -23dBFS peak) through the
model, and compare each rung's octave-band levels with the real capture.

    python validate.py --audio-root <folder containing reamps/>

The error is dB RMS over rungs and octaves 31.5Hz-8kHz, with one gain offset
per take allowed (the source project's `abs_rms`). Writes validation.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from model import TidalWave  # noqa: E402
from rig_dsp import run, stimuli as st, sweep as sw  # noqa: E402

CASES = [("TW29", "7:00", "max", "fitted"), ("TW09", "9:00", "max", "fitted"),
         ("TW30", "11:00", "max", "fitted"), ("TW32", "max", "max", "fitted"),
         ("TW02", "9:00", "12:00", "Blend 12:00 calibration take (a, b, tau fitted here)"),
         ("TW03", "7:00", "12:00", "held out (Blend 12:00)"),
         ("TW06", "max", "12:00", "held out (Blend 12:00)")]
OCT = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]


def octave_levels(y, layout, sr):
    out = []
    for a in layout.starts:
        seg = y[a:a + int(layout.sweep_seconds * sr)]
        f, p = signal.welch(seg, sr, nperseg=8192)
        out.append([10 * np.log10(p[(f >= c / 2 ** .5) & (f < c * 2 ** .5)].sum() + 1e-30)
                    for c in OCT])
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-root", type=Path, required=True)
    root = ap.parse_args().audio_root.resolve()
    tw = TidalWave.load()
    x = st.ess_ladder().astype(np.float64)
    x = x / np.max(np.abs(x)) * 10 ** (-23 / 20)
    res = {}
    with run.Progress(total=len(CASES), name="validate_tidal_wave") as prog:
        for take, drive, blend, role in CASES:
            y, sr = sw.load(root / "reamps" / f"{take}_ess_ladder_lad.wav")
            pred = tw.apply(x, drive, blend)
            lp, ly = sw.locate(pred, sr, "ess_ladder"), sw.locate(y, sr, "ess_ladder")
            d = octave_levels(pred, lp, sr) - octave_levels(y, ly, sr)
            d -= np.median(d)
            res[take] = {"drive": drive, "blend": blend, "role": role,
                         "abs_rms_db": round(float(np.sqrt(np.mean(d ** 2))), 2),
                         "per_rung_rms_db": [round(float(np.sqrt(np.mean(r ** 2))), 2) for r in d]}
            prog.step(note=f"{take} {res[take]['abs_rms_db']}")
    (HERE / "validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for t, v in res.items():
        print(t, v)


if __name__ == "__main__":
    main()
