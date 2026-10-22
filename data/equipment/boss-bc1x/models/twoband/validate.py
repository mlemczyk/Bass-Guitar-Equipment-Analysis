#!/usr/bin/env python3
"""
Check the published BC-1X model against the captures.

    python validate.py --audio-root <folder containing reamps/>

Runs the bypass capture (BC15) through the model and compares the result with
the real pedal (BC01): the 5ms envelope error on played frames, for the played
performance (which the dynamics were fitted on) and the synthetic plucks
(never fitted). Writes validation.json. The music audio is not published, so
this needs the source captures. The plucks are a published probe.
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
sys.path.insert(0, str(HERE))

from model import apply_model, load_params  # noqa: E402
from rig_dsp import envelope as ev, run, sweep as sw  # noqa: E402


def compare(root, probe):
    x, sr = sw.load(root / "reamps" / f"BC15_{probe}_lad.wav")
    y, _ = sw.load(root / "reamps" / f"BC01_{probe}_lad.wav")
    a, b, _, pol = ev.align(x, y, m=min(400000, len(x)))
    sim = apply_model(a, load_params(), sr) * pol
    n = ev.frame_len(sr)
    es, er = ev.env_db(sim, n), ev.env_db(b, n)
    k = min(len(es), len(er))
    live = (es[:k] > -55) & (er[:k] > -55)
    crest = lambda z: 20 * np.log10(np.max(np.abs(z)) / np.sqrt(np.mean(z ** 2)))  # noqa: E731
    return {"envelope_rms_db_played_frames": round(float(np.sqrt(np.mean(
                (es[:k] - er[:k])[live] ** 2))), 3),
            "crest_error_db": round(float(crest(sim) - crest(b)), 3),
            "level_error_db": round(float(10 * np.log10(np.mean(sim ** 2) / np.mean(b ** 2))), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio-root", type=Path, required=True)
    root = ap.parse_args().audio_root.resolve()
    out = {}
    with run.Progress(total=2, name="validate_bc1x") as prog:
        for probe, role in (("music", "fitted (dynamics)"), ("plucks", "held out")):
            out[probe] = {"role": role, **compare(root, probe)}
            prog.step(note=probe)
    src = json.loads((HERE / "params.json").read_text(encoding="utf-8"))
    doc = {"this_port": out, "source_project_fit": src.get("source_fit_report")}
    (HERE / "validation.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
