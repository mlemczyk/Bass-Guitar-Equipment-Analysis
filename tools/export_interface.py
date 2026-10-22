#!/usr/bin/env python3
"""
Export the re-amp loop's own measurements to interface/measurements/.

    python tools/export_interface.py --audio-root "<folder holding reamps/>"

  LOOP-NULL     L01: ess.wav through every stage bypassed, against the digital
                probe itself. The loop's round-trip response.
  LOOP-NOISE    L03: silence.wav through the loop. Its noise floor.
  LOOP-LEVELS   MYTH01_levels_lad: the 110Hz level-steps probe with every
                pedal bypassed. Where the loop itself starts to distort.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sg

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from rig_dsp import run, stimuli as st, sweep as sw  # noqa: E402
import export_eq_seeker as es  # noqa: E402

OUT = REPO / "interface" / "measurements"


def loop_null(root):
    p = root / "reamps" / "L01.wav"
    rec, sr = sw.load(p)
    lt = sw.locate(rec, sr, "ess")
    probe = st.norm(st.exponential_sweep(sr=sr)[0]).astype(np.float64)
    # the digital probe as its own "capture", so the same Farina code divides it out
    pad = np.concatenate([np.zeros(lt.starts[0]), probe, np.zeros(sr * 2)])
    lp = sw.locate(pad, sr, "ess")
    ft, fp = sw.farina_rung(rec, sr, lt, 0), sw.farina_rung(pad, sr, lp, 0)
    grid = sw.log_grid(20, 20000, 12)
    mag, ph = sw.smooth_complex(ft["f"], ft["H1"] / (fp["H1"] + 1e-30), grid)
    return {"take_id": "LOOP-NULL", "source_take_id": "L01",
            "description": "ess.wav through the whole re-amp loop, every pedal bypassed, "
                           "against the digital probe",
            "capture": {"file": "reamps/L01.wav", "sha256": es.sha256(p), "sample_rate": sr,
                        "probe": "ess", "send_peak_dbfs": None},
            "return_peak_dbfs": es.r(sw.peak_dbfs(rec)),
            "farina_grid_hz": [es.r(g, 2) for g in grid],
            "farina_db": [es.r(m) for m in mag],
            "farina_phase_deg": [es.r(np.degrees(x), 1) for x in ph],
            "noise": es.noise_block(rec, sr, lt)}


def loop_noise(root):
    p = root / "reamps" / "L03.wav"
    rec, sr = sw.load(p)
    body = rec[int(0.5 * sr):-int(0.5 * sr)]
    b, a = sg.butter(4, [20, 20000], btype="band", fs=sr)
    f, pw = sg.welch(body, sr, nperseg=8192)
    fo, db = sw.third_octave(f, 10 * np.log10(pw * (f[1] - f[0]) * 1.5 + 1e-30),
                             np.ones_like(f, dtype=bool), lo=-17, hi=14)
    return {"take_id": "LOOP-NOISE", "source_take_id": "L03",
            "description": "silence.wav through the whole loop, every pedal bypassed",
            "capture": {"file": "reamps/L03.wav", "sha256": es.sha256(p), "sample_rate": sr,
                        "probe": "silence"},
            "noise": {"seconds": es.r(len(body) / sr), "rms_dbfs_20_20k":
                      es.r(sw.rms_dbfs(sg.filtfilt(b, a, body))),
                      "third_octave_dbfs": [[es.r(x, 1), es.r(y)] for x, y in zip(fo, db)]}}


def loop_levels(root):
    res = es.analyse_levels({"root": str(root), "file": "reamps/MYTH01_levels_lad.wav",
                             "key": "LOOP-LEVELS", "take_id": "LOOP-LEVELS"})
    res.pop("key")
    res["source_take_id"] = "MYTH01 (levels probe, every pedal bypassed)"
    res["description"] = ("110Hz level steps through the whole loop, every pedal bypassed: "
                          "the loop's own distortion against return level")
    res["capture"]["send_peak_dbfs"] = -23.0
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audio-root", type=Path,
                    default=Path(os.environ.get("RIG_AUDIO_ROOT", ".")))
    args = ap.parse_args()
    root = args.audio_root.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [loop_null, loop_noise, loop_levels]
    with run.Progress(total=len(jobs), name="export_interface") as prog:
        for fn in jobs:
            doc = {"schema": "rig-equipment/loop@1", **fn(root)}
            (OUT / f"{doc['take_id']}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            prog.step(note=doc["take_id"])


if __name__ == "__main__":
    main()
