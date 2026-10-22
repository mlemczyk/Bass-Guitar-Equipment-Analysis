#!/usr/bin/env python3
"""
Export every capture of one pedal to per-take measurement files.

    python tools/export_pedal.py joyo-r22-tidal-wave --audio-root "<folder holding reamps/>"
    python tools/export_pedal.py all --audio-root ...

The take table (control, value, what was held fixed) is tools/takes/<pedal>.json,
taken from the source project's recording matrix.

REFERENCE RULE. Every ratio is against the WHOLE LOOP WITH EVERY PEDAL
BYPASSED, using the capture with the same probe and send level that was
recorded closest in time. The bypass takes of every pedal (TW01, MUFF01,
MYTH01, BC15) are that same state, so all four are candidates. The chosen
reference and the days between the two captures are in each capture's
`reference` block. To compare two settings of one pedal, divide their
responses (both are against bypass).

Per probe:
  ess_ladder        Farina + legacy response per rung vs bypass, harmonics, noise
  levels            per-step fundamental, harmonics and THD (absolute), and gain vs bypass
  music             (a played song, never published) frame percentiles, per-class gain,
                    octave band gain on played frames; frame envelopes -> envelopes.npz
  bursts, plucks    frame envelopes of take and reference -> envelopes.npz
  twotone           per step: level of each probe tone and of the 80Hz tone
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

from rig_dsp import envelope as ev, run, stimuli as st, sweep as sw  # noqa: E402
import export_eq_seeker as es  # noqa: E402
import export_nr300 as en  # noqa: E402

PEDALS = ["boss-bc1x", "joyo-r22-tidal-wave", "joyo-r26-monomyth", "ehx-deluxe-bass-big-muff"]
BYPASS_TAKES = ["TW01", "MUFF01", "MYTH01", "BC15"]
# send peak by capture tag (source project's `reamp.py --level` convention)
SEND = {"lad": -23.0, "lad30": -30.0, "lad30_drift": -30.0}
NAME_RE = re.compile(r"^(?P<tid>[A-Z]+\d+)_(?P<probe>ess_ladder|levels|music|bursts|plucks|"
                     r"twotone)(?:_(?P<tag>.+))?$")
SKIP = re.compile(r"^INVALID_")


def parse(p: Path):
    m = NAME_RE.match(p.stem)
    return (m["tid"], m["probe"], m["tag"] or "") if m else None


def mtime(p: Path):
    return datetime.fromtimestamp(p.stat().st_mtime)


def pick_reference(root: Path, probe, tag, when):
    best = None
    for t in BYPASS_TAKES:
        for p in (root / "reamps").glob(f"{t}_{probe}*.wav"):
            k = parse(p)
            if not k or k[1] != probe or k[2] != tag:
                continue
            dt = abs((mtime(p) - when).total_seconds())
            if best is None or dt < best[0]:
                best = (dt, p, t)
    return best


# ------------------------------------------------------------------ per probe

def do_levels(job):
    root = Path(job["root"])
    a = es.analyse_levels({"root": job["root"], "file": job["file"], "key": job["key"],
                           "take_id": job["take_id"]})
    a["capture"]["tag"] = job["tag"] or None
    a["capture"]["send_peak_dbfs"] = SEND.get(job["tag"])
    if job.get("ref_file"):
        b = es.analyse_levels({"root": job["root"], "file": job["ref_file"], "key": "ref",
                               "take_id": "ref"})
        a["reference"] = job["ref_block"]
        for s, r in zip(a["steps"], b["steps"]):
            s["reference_fundamental_dbfs_peak"] = r["fundamental_dbfs_peak"]
            s["reference_thd_pct_h2_h5"] = r["thd_pct_h2_h5"]
            s["gain_vs_reference_db"] = es.r(s["fundamental_dbfs_peak"] - r["fundamental_dbfs_peak"])
    return a


def do_music(job):
    root = Path(job["root"])
    pr, pt = root / job["ref_file"], root / job["file"]
    xr, sr = sw.load(pr)
    yt, _ = sw.load(pt)
    n = ev.frame_len(sr)
    a, b, lag, pol = ev.align(xr, yt)
    xe, ye = ev.env_db(a, n), ev.env_db(b, n)
    k = min(len(xe), len(ye))
    xe, ye = xe[:k], ye[:k]
    ref_p = np.percentile(xe, en.PCTS)
    d = ye - xe
    cls = {"music": xe > en.MUSIC_DB, "transition": (xe <= en.MUSIC_DB) & (xe > en.REST_DB),
           "rest": xe <= en.REST_DB}
    out = {"key": job["key"], "take_id": job["take_id"],
           "capture": {**job["cap"], "probe": "music"},
           "reference": job["ref_block"],
           "alignment": {"lag_samples": int(lag),
                         "polarity_vs_reference": "inverted" if pol < 0 else "same"},
           "peak_dbfs": {"positive": es.r(20 * np.log10(b.max())),
                         "negative": es.r(20 * np.log10(-b.min()))},
           "rms_gain_db": es.r(10 * np.log10(np.mean(b ** 2) / np.mean(a ** 2))),
           "frame_percentiles": {"frame_ms": ev.FRAME_MS,
                                 "reference_dbfs": {f"p{p}": es.r(v) for p, v in zip(en.PCTS, ref_p)},
                                 "change_db": {f"p{p}": es.r(v) for p, v in
                                               zip(en.PCTS, np.percentile(ye, en.PCTS) - ref_p)}},
           "frame_gain_db_by_class": {c: {"frames": int(s.sum()),
                                          "median": es.r(np.median(d[s])) if s.any() else None,
                                          "p10": es.r(np.percentile(d[s], 10)) if s.any() else None,
                                          "p90": es.r(np.percentile(d[s], 90)) if s.any() else None}
                                      for c, s in cls.items()},
           "musical_frames_band_gain": en.band_gain(a, b, xe > en.MUSIC_DB, n, sr),
           "_env": {"x_rms": xe, "key_peak": ev.peak_db(a, n)[:k], "y_rms": ye}}
    return out


def do_envelope(job):
    """bursts / plucks: frame envelopes of take and (aligned) reference."""
    root = Path(job["root"])
    yt, sr = sw.load(root / job["file"])
    n = ev.frame_len(sr)
    out = {"key": job["key"], "take_id": job["take_id"], "capture": job["cap"],
           "peak_dbfs": {"positive": es.r(20 * np.log10(yt.max())),
                         "negative": es.r(20 * np.log10(-yt.min()))},
           "envelope": f"envelopes.npz: {job['take_id']}/{job['probe']}{'_' + job['tag'] if job['tag'] else ''}/*"}
    if job.get("ref_file"):
        xr, _ = sw.load(root / job["ref_file"])
        a, b, lag, pol = ev.align(xr, yt, m=len(xr))
        out["reference"] = job["ref_block"]
        out["alignment"] = {"lag_samples": int(lag),
                            "polarity_vs_reference": "inverted" if pol < 0 else "same"}
        k = min(len(a), len(b)) // n
        out["_env"] = {"x_rms": ev.env_db(a, n)[:k], "y_rms": ev.env_db(b, n)[:k]}
    else:
        out["reference"] = None
        out["_env"] = {"y_rms": ev.env_db(yt, n)}
    return out


def do_twotone(job):
    root = Path(job["root"])
    y, sr = sw.load(root / job["file"])
    probe = st.two_tone(sr=sr).astype(np.float64) * 10 ** ((SEND.get(job["tag"], -12.0) - (-12.0)) / 20)
    m = min(len(y), len(probe) + 4 * sr)
    size = 1 << int(np.ceil(np.log2(m + len(probe))))
    corr = np.fft.irfft(np.fft.rfft(y[:m], size) * np.conj(np.fft.rfft(probe, size)), size)
    start = int(np.argmax(np.abs(corr[:max(m - len(probe) + 1, 1)])))
    rows = []
    pos = start + int(1.0 * sr)
    for db in st.TWOTONE_LOW_STEPS:
        nstep = int(st.TWOTONE_STEP_SEC * sr)
        seg = y[pos + int(0.5 * sr):pos + nstep - int(0.25 * sr)]
        w = np.hanning(len(seg))
        spec = np.abs(np.fft.rfft(seg * w)) * 2 / np.sum(w)
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        lvl = lambda hz: es.r(20 * np.log10(spec[int(np.argmin(np.abs(f - hz)))] + 1e-12))  # noqa: E731
        rows.append({"low_tone_file_dbfs": db, "low_80hz_dbfs": lvl(st.TWOTONE_LOW_HZ),
                     **{f"probe_{int(h)}hz_dbfs": lvl(h) for h in st.TWOTONE_PROBE_HZ}})
        pos += nstep + int(st.TWOTONE_GAP_SEC * sr)
    return {"key": job["key"], "take_id": job["take_id"], "capture": job["cap"],
            "reference": None, "steps": rows}


def do_sweep(job):
    res = es.analyse_sweep(job)
    res["capture"]["send_peak_dbfs"] = job["send_peak"]
    res["reference"].update({k: v for k, v in job["ref_block"].items() if k not in res["reference"]})
    return res


WORK = {"ess_ladder": do_sweep, "levels": do_levels, "music": do_music,
        "bursts": do_envelope, "plucks": do_envelope, "twotone": do_twotone}


def work(job):
    return WORK[job["probe"]](job)


# ------------------------------------------------------------------ jobs

def jobs_for(eq, root: Path):
    cfg = json.loads((REPO / "tools" / "takes" / f"{eq}.json").read_text(encoding="utf-8"))
    ids = {t["take_id"] for t in cfg["takes"]}
    jobs = []
    for p in sorted((root / "reamps").glob(f"{cfg['prefix']}*.wav")):
        if SKIP.match(p.name):
            continue
        k = parse(p)
        if not k or k[0] not in ids:
            continue
        tid, probe, tag = k
        cap = {"file": es.rel(p, root), "sha256": es.sha256(p), "probe": probe,
               "tag": tag or None, "recorded": mtime(p).strftime("%Y-%m-%d"),
               "send_peak_dbfs": SEND.get(tag)}
        job = {"root": str(root), "take_id": tid, "file": es.rel(p, root), "probe": probe,
               "tag": tag, "key": f"{tid}:{p.stem}", "cap": cap,
               "tag_key": f"{probe}_{tag}", "send_peak": SEND.get(tag)}
        ref = pick_reference(root, probe, tag, mtime(p))
        if ref and ref[1] != p:
            dt, rp, rt = ref
            job["ref_file"], job["ref_take"] = es.rel(rp, root), rt
            job["ref_block"] = {"take_id": rt, "file": es.rel(rp, root),
                                "state": "every pedal bypassed",
                                "recorded": mtime(rp).strftime("%Y-%m-%d"),
                                "days_apart": round(dt / 86400, 2)}
        elif ref and ref[1] == p:
            # the bypass capture itself: describe it against the nearest OTHER bypass
            others = [q for q in BYPASS_TAKES if q != tid]
            best = None
            for t in others:
                for q in (root / "reamps").glob(f"{t}_{probe}*.wav"):
                    kq = parse(q)
                    if kq and kq[1] == probe and kq[2] == tag:
                        d = abs((mtime(q) - mtime(p)).total_seconds())
                        if best is None or d < best[0]:
                            best = (d, q, t)
            if best:
                job["ref_file"], job["ref_take"] = es.rel(best[1], root), best[2]
                job["ref_block"] = {"take_id": best[2], "file": es.rel(best[1], root),
                                    "state": "every pedal bypassed (another session: loop drift)",
                                    "recorded": mtime(best[1]).strftime("%Y-%m-%d"),
                                    "days_apart": round(best[0] / 86400, 2)}
        if probe in ("ess_ladder", "music") and "ref_file" not in job:
            continue                      # nothing to divide by
        jobs.append(job)
    return cfg, jobs


def write(eq, cfg, results):
    out = REPO / "data" / "equipment" / eq / "measurements"
    out.mkdir(parents=True, exist_ok=True)
    arrays = {}
    n = 0
    for t in cfg["takes"]:
        caps = [r for r in results if r["take_id"] == t["take_id"]]
        if not caps:
            continue
        for c in caps:
            env = c.pop("_env", None)
            if env:
                stem = Path(c["capture"]["file"]).stem.split("_", 1)[1]
                for k, v in env.items():
                    arrays[f"{t['take_id']}/{stem}/{k}"] = ev.to_cdb(v)
        doc = {"schema": "rig-equipment/take@1", "equipment": eq, "take_id": t["take_id"],
               "description": f"{t['control']}: {t['value']}",
               "settings": {"control": t["control"], "value": t["value"],
                            "everything_else": t["held_fixed"],
                            "settled_values": cfg["settled"]},
               "captures": [{k: v for k, v in c.items() if k not in ("key", "take_id")}
                            for c in sorted(caps, key=lambda c: c["capture"]["file"])]}
        (out / f"{t['take_id']}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
        n += 1
    if arrays:
        np.savez_compressed(out / "envelopes.npz", frame_ms=np.array(ev.FRAME_MS),
                            units=np.array("centi-dB (divide by 100 for dB / dBFS)"), **arrays)
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pedal", choices=PEDALS + ["all"])
    ap.add_argument("--audio-root", type=Path,
                    default=Path(os.environ.get("RIG_AUDIO_ROOT", ".")))
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    root = args.audio_root.resolve()
    pedals = PEDALS if args.pedal == "all" else [args.pedal]
    plan = {eq: jobs_for(eq, root) for eq in pedals}
    jobs = [j for _, js in plan.values() for j in js]
    run.pin_blas()
    nw = run.workers(1.5, jobs=len(jobs), requested=args.workers, name="export_pedal")
    results = {}
    with run.Progress(total=len(jobs), name="export_pedal") as prog, \
            ProcessPoolExecutor(max_workers=nw) as ex:
        futs = {ex.submit(work, j): j for j in jobs}
        for fu in as_completed(futs):
            j = futs[fu]
            try:
                results[j["key"]] = fu.result()
            except Exception as e:  # report and keep going; a missing capture is listed
                print(f"FAILED {j['key']}: {e!r}", flush=True)
            prog.step(note=j["key"])
    for eq, (cfg, js) in plan.items():
        keys = {j["key"] for j in js}
        n = write(eq, cfg, [r for k, r in results.items() if k in keys])
        print(f"{eq}: {n} take files")


if __name__ == "__main__":
    main()
