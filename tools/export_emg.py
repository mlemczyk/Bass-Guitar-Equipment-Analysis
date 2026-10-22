#!/usr/bin/env python3
"""
Export the EMG BQC injection measurements and the Y-split validation.

    python tools/export_emg.py --audio-root "<folder holding raw_takes/ and measurements/>"

The EMG curves were computed in the source project by `emg_sweep.py` (each
take's sweep divided by the EMG-flat reference H00, with the transducer
injecting magnetically into the pickups). This copies those results into the
repository schema, adds the audio hash, and drops local paths. Y01-Y07 (the
Y-split cable check) go to interface/measurements/.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from rig_dsp import run  # noqa: E402
import export_eq_seeker as es  # noqa: E402

OUT = REPO / "data" / "equipment" / "emg-bqc" / "measurements"
OUT_Y = REPO / "interface" / "measurements"

SETTINGS = {  # take -> (control, position, MidFreq)
    "H00": ("flat reference", 0, None), "H99": ("closing reference (= H00)", 0, None),
    "H01": ("Bass", -5, None), "H02": ("Bass", -2, None), "H03": ("Bass", 2, None),
    "H04": ("Bass", 5, None), "H05": ("Treble", -5, None), "H06": ("Treble", -2, None),
    "H07": ("Treble", 2, None), "H08": ("Treble", 5, None),
    "H09": ("Mid", -5, -5), "H10": ("Mid", -2, -5), "H11": ("Mid", 2, -5), "H12": ("Mid", 5, -5),
    "H13": ("Mid", -5, 0), "H14": ("Mid", -2, 0), "H15": ("Mid", 2, 0), "H16": ("Mid", 5, 0),
    "H17": ("Mid", -5, 5), "H18": ("Mid", -2, 5), "H19": ("Mid", 2, 5), "H20": ("Mid", 5, 5),
    "H21": ("Mid", 5, -2.5), "H22": ("Mid", 5, 2.5),
}


def emg_settings(tid):
    ctl, pos, mf = SETTINGS[tid]
    s = {"bass": 0, "mid": 0, "midfreq": 0, "treble": 0, "pickup_pan": 0,
         "treble_dip_sw1_sw2": "OFF/OFF"}
    if ctl in ("Bass", "Treble", "Mid"):
        s[ctl.lower()] = pos
    if mf is not None:
        s["midfreq"] = mf
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-root", type=Path,
                    default=Path(os.environ.get("RIG_AUDIO_ROOT", ".")))
    root = ap.parse_args().audio_root.resolve()
    src = root / "measurements"
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_Y.mkdir(parents=True, exist_ok=True)
    matrix = {r["take_id"]: r for r in csv.DictReader(
        open(root / "recording_matrix.csv", encoding="utf-8"))}
    jobs = sorted(SETTINGS) + [f"Y0{i}" for i in (1, 2, 3, 5, 6, 7)]
    with run.Progress(total=len(jobs), name="export_emg") as prog:
        for tid in jobs:
            p = src / f"{tid}.json"
            if not p.exists():
                prog.step(note=f"{tid} missing")
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            if tid.startswith("H"):
                wav = root / "raw_takes" / d["file"]
                doc = {"schema": "rig-equipment/take@1", "equipment": "emg-bqc", "take_id": tid,
                       "description": f"{SETTINGS[tid][0]} {SETTINGS[tid][1]:+g}"
                       + (f" at MidFreq {SETTINGS[tid][2]:+g}" if SETTINGS[tid][2] is not None else ""),
                       "settings": emg_settings(tid),
                       "captures": [{
                           "capture": {"file": f"raw_takes/{d['file']}",
                                       "sha256": es.sha256(wav) if wav.exists() else None,
                                       "probe": "emg_sweep (magnetic injection)",
                                       "sweeps_found": d.get("sweeps_found"),
                                       "peak_dbfs": d.get("peak_dbfs"),
                                       "noise_floor_dbfs": d.get("noise_floor_dbfs"),
                                       "duration_s": d.get("duration_sec"),
                                       "recorded": "2026-09-13"},
                           "reference": {"take_id": d.get("reference")},
                           "curve_db": d.get("curve_db"),
                           "summary": d.get("summary"),
                           "session_drift_db": d.get("session_drift_db")}]}
                (OUT / f"{tid}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
            else:
                row = matrix.get(tid, {})
                out = {k: v for k, v in d.items() if k not in ("source", "output", "source_folder",
                                                                "tone", "tone_source", "n_notes")}
                out.update({"schema": "rig-equipment/loop@1", "take_id": f"YSPLIT-{tid}",
                            "source_take_id": tid, "description": row.get("value"),
                            "capture": {"file": "raw_takes/" + Path(d["output"]).name,
                                        "probe": "emg_sweep / played"}})
                (OUT_Y / f"YSPLIT-{tid}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
            prog.step(note=tid)


if __name__ == "__main__":
    main()
