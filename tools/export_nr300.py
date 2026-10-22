#!/usr/bin/env python3
"""
Export the Behringer NR300 captures to per-take measurement files.

    python tools/export_nr300.py --audio-root "<folder holding reamps/>"

Each take NR02-NR08 is the same re-amp through the gate at one setting; NR01 is
the gate switched off (held open). Every take has two captures:

  music   R03 re-amped: a fingerstyle performance of Linkin Park - With You,
          ~218s. The audio is not published. Its 5ms frame envelopes are, in
          measurements/envelopes.npz, and models/expander/fit.py fits to them.
  levels  the 110Hz level-steps probe.

Writes measurements/NRnn.json (schema `rig-equipment/take@1`, gate captures)
and measurements/envelopes.npz.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy import signal

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from rig_dsp import envelope as ev, run, sweep as sw  # noqa: E402
import export_eq_seeker as es  # noqa: E402

EQUIPMENT = "behringer-nr300"
OUT = REPO / "data" / "equipment" / EQUIPMENT / "measurements"
REF = "NR01"


def setting(on=True, thr="9:00", dec="7:00"):
    return {"noise_reduction": "on" if on else "off",
            "threshold": thr if on else None, "decay": dec if on else None}


TAKES = {
    "NR01": (setting(on=False), "noise reduction OFF, gate held open: the reference"),
    "NR02": (setting(), "Threshold 9:00, Decay 7:00"),
    "NR03": (setting(thr="min"), "Threshold min, Decay 7:00"),
    "NR04": (setting(thr="12:00"), "Threshold 12:00, Decay 7:00"),
    "NR05": (setting(thr="3:00"), "Threshold 3:00, Decay 7:00"),
    "NR06": (setting(thr="max"), "Threshold max, Decay 7:00"),
    "NR07": (setting(dec="12:00"), "Threshold 9:00, Decay 12:00"),
    "NR08": (setting(dec="max"), "Threshold 9:00, Decay max"),
}
# A tonal interferer at ~415/829Hz under the open gate on musical frames,
# present in NR02 and NR05 only; it is the recording, not the pedal.
CONTAMINATED = {"NR02", "NR05"}
MUSIC_DB, REST_DB = -60.0, -85.0
PCTS = (1, 10, 25, 50, 75, 95)
OCTAVES = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]


def steps(xe, ye):
    """Per level step: median input frame level and median gain (out - in),
    over the steady core of each step."""
    on = xe > xe.max() - 45
    runs, s0 = [], None
    for i, v in enumerate(on):
        if v and s0 is None:
            s0 = i
        elif not v and s0 is not None:
            if i - s0 > 150:
                runs.append((s0, i))
            s0 = None
    out = []
    for s, f in runs:
        core = slice(s + 60, f - 40)
        out.append({"input_frame_rms_dbfs": es.r(np.median(xe[core])),
                    "gain_db": es.r(np.median(ye[core] - xe[core]))})
    return out


def band_gain(x, y, sel, n, sr):
    keep = np.repeat(sel, n)
    m = min(len(keep), len(x))
    xs, ys = x[:m][keep[:m]], y[:m][keep[:m]]
    f, pxx = signal.welch(xs, sr, nperseg=8192)
    _, pyy = signal.welch(ys, sr, nperseg=8192)
    _, pxy = signal.csd(xs, ys, sr, nperseg=8192)
    _, coh = signal.coherence(xs, ys, sr, nperseg=8192)
    rows = []
    for fc in OCTAVES:
        s = (f >= fc / 2 ** 0.5) & (f < min(fc * 2 ** 0.5, sr / 2))
        rows.append({"centre_hz": fc,
                     "power_db": es.r(10 * np.log10(pyy[s].sum() / pxx[s].sum())),
                     "coherent_db": es.r(20 * np.log10(np.abs(pxy[s].sum()) / pxx[s].sum())),
                     "coherence": es.r(np.mean(coh[s]), 3),
                     "input_level_dbfs": es.r(10 * np.log10(pxx[s].sum() * (f[1] - f[0]) + 1e-30))})
    return rows


def analyse(job):
    root, tid = Path(job["root"]), job["take_id"]
    out = {"take_id": tid, "captures": [], "env": {}}
    for probe in ("music", "levels"):
        pr, pt = root / "reamps" / f"{REF}_{probe}.wav", root / "reamps" / f"{tid}_{probe}.wav"
        xr, sr = sw.load(pr)
        yt, sr2 = sw.load(pt)
        assert sr == sr2
        n = ev.frame_len(sr)
        if tid == REF:
            a, b, lag, pol = xr, yt, 0, 1.0
        else:
            a, b, lag, pol = ev.align(xr, yt, m=400000 if probe == "music" else len(xr))
        xe, ye = ev.env_db(a, n), ev.env_db(b, n)
        k = min(len(xe), len(ye))
        xe, ye = xe[:k], ye[:k]
        cap = {"capture": {"file": f"reamps/{tid}_{probe}.wav", "sha256": es.sha256(pt),
                           "sample_rate": sr, "probe": probe, "tag": None,
                           "recorded": es.datetime.fromtimestamp(pt.stat().st_mtime)
                           .strftime("%Y-%m-%d"),
                           "duration_s": es.r(len(yt) / sr, 2),
                           "contaminated": ("tonal interferer ~415/829Hz on musical frames, "
                                            "from the recording, not the pedal")
                           if (tid in CONTAMINATED and probe == "music") else None},
               "reference": {"take_id": REF, "file": f"reamps/{REF}_{probe}.wav",
                             "sha256": es.sha256(pr)},
               "alignment": {"lag_samples": int(lag),
                             "polarity_vs_reference": "inverted" if pol < 0 else "same"},
               "peak_dbfs": {"positive": es.r(20 * np.log10(b.max())),
                             "negative": es.r(20 * np.log10(-b.min()))}}
        if probe == "music":
            ref_p = np.percentile(xe, PCTS)
            cap["frame_percentiles"] = {
                "frame_ms": ev.FRAME_MS,
                "reference_dbfs": {f"p{p}": es.r(v) for p, v in zip(PCTS, ref_p)},
                "change_db": {f"p{p}": es.r(v) for p, v in
                              zip(PCTS, np.percentile(ye, PCTS) - ref_p)}}
            d = ye - xe
            cls = {"music": xe > MUSIC_DB, "transition": (xe <= MUSIC_DB) & (xe > REST_DB),
                   "rest": xe <= REST_DB}
            cap["frame_gain_db_by_class"] = {
                c: {"frames": int(s.sum()), "median": es.r(np.median(d[s])) if s.any() else None,
                    "p10": es.r(np.percentile(d[s], 10)) if s.any() else None}
                for c, s in cls.items()}
            cap["musical_frames_band_gain"] = band_gain(a, b, xe > MUSIC_DB, n, sr) \
                if tid != REF else None
            out["env"]["music"] = {"x_rms": xe, "key_rms": xe, "key_peak": ev.peak_db(a, n)[:k],
                                   "y_rms": ye}
        else:
            cap["steps"] = steps(xe, ye)
            out["env"]["levels"] = {"x_rms": xe, "key_rms": xe, "key_peak": ev.peak_db(a, n)[:k],
                                    "y_rms": ye}
        out["captures"].append(cap)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audio-root", type=Path,
                    default=Path(os.environ.get("RIG_AUDIO_ROOT", ".")))
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    root = args.audio_root.resolve()
    jobs = [{"root": str(root), "take_id": t} for t in TAKES]
    run.pin_blas()
    n = run.workers(1.5, jobs=len(jobs), requested=args.workers, name="export_nr300")
    res = {}
    with run.Progress(total=len(jobs), name="export_nr300") as prog, \
            ProcessPoolExecutor(max_workers=n) as ex:
        for r in ex.map(analyse, jobs):
            res[r["take_id"]] = r
            prog.step(note=r["take_id"])

    OUT.mkdir(parents=True, exist_ok=True)
    arrays = {}
    for tid, (settings, desc) in TAKES.items():
        r = res[tid]
        doc = {"schema": "rig-equipment/take@1", "equipment": EQUIPMENT, "take_id": tid,
               "description": desc, "settings": settings, "captures": r["captures"]}
        (OUT / f"{tid}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        for probe, d in r["env"].items():
            for k, v in d.items():
                arrays[f"{tid}/{probe}/{k}"] = ev.to_cdb(v)
    np.savez_compressed(OUT / "envelopes.npz", frame_ms=np.array(ev.FRAME_MS),
                        units=np.array("centi-dB (divide by 100 for dB / dBFS)"), **arrays)
    print(f"wrote {len(TAKES)} take files and envelopes.npz to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
