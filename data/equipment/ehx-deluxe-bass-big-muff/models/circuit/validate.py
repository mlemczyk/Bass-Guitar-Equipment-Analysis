#!/usr/bin/env python3
"""
Check the port: feed the Blend-min capture of the 110Hz level steps (MUFF14)
through the model and compare each step's fundamental and odd harmonics with
the real Blend-max captures.

    python validate.py --audio-root <folder containing reamps/>

Prints and appends `port_check` to validation.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(HERE))

from model import BigMuff  # noqa: E402
from rig_dsp import run, sweep as sw  # noqa: E402
import export_eq_seeker as es  # noqa: E402

CASES = [("MUFF16", "12:00", "max", "fitted"), ("MUFF07", "min", "max", "fitted"),
         ("MUFF10", "max", "max", "fitted"), ("MUFF11", "12:00", "min", "fitted"),
         ("MUFF08", "9:00", "max", "held out"), ("MUFF09", "3:00", "max", "held out"),
         ("MUFF12", "12:00", "9:00", "held out"), ("MUFF13", "12:00", "12:00", "held out"),
         ("MUFF28", "max", "min", "held out")]


def steps_of(y, root, sr):
    tmp = root / "_tmp_validate.wav"
    import soundfile as sf
    sf.write(tmp, y, sr, subtype="FLOAT")
    try:
        r = es.analyse_levels({"root": str(root), "file": tmp.name, "key": "x", "take_id": "x"})
    finally:
        tmp.unlink()
    return r["steps"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-root", type=Path, required=True)
    root = ap.parse_args().audio_root.resolve()
    m = BigMuff.load()
    x, sr = sw.load(root / "reamps" / "MUFF14_levels_lad.wav")
    out = {}
    with run.Progress(total=len(CASES), name="validate_big_muff") as prog:
        for take, sus, tone, role in CASES:
            real = es.analyse_levels({"root": str(root), "file": f"reamps/{take}_levels_lad.wav",
                                      "key": take, "take_id": take})["steps"]
            pred = steps_of(m.apply(x, sr, sus, tone, "max"), HERE, sr)
            d1 = [p["fundamental_dbfs_peak"] - r_["fundamental_dbfs_peak"] for p, r_ in zip(pred, real)]
            d3 = [p["harmonics_db_rel_fundamental"]["h3"] - r_["harmonics_db_rel_fundamental"]["h3"]
                  for p, r_ in zip(pred, real)]
            out[take] = {"sustain": sus, "tone": tone, "role": role,
                         "fundamental_err_db": [round(v, 2) for v in d1],
                         "h3_err_db": [round(v, 2) for v in d3],
                         "fundamental_rms_db": round(float(np.sqrt(np.mean(np.square(d1)))), 2),
                         "h3_rms_db": round(float(np.sqrt(np.mean(np.square(d3)))), 2)}
            prog.step(note=f"{take} {out[take]['fundamental_rms_db']}")
    v = json.loads((HERE / "validation.json").read_text(encoding="utf-8"))
    v["port_check_levels_probe"] = out
    (HERE / "validation.json").write_text(json.dumps(v, indent=1), encoding="utf-8")
    for t, r in out.items():
        print(t, r["role"], "fundamental", r["fundamental_rms_db"], "h3", r["h3_rms_db"])


if __name__ == "__main__":
    main()
