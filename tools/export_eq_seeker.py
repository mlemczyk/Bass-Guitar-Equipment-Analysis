#!/usr/bin/env python3
"""
Export every Donner EQ Seeker capture to per-take measurement JSON.

    python tools/export_eq_seeker.py --audio-root "<folder holding reamps/>"

Reads the re-amp captures (`reamps/SEEK*.wav`), analyses each against its
reference, and writes `data/equipment/donner-eq-seeker/measurements/SEEKnn.json`.
Captures are analysed in parallel; see rig_dsp/run.py.

Schema: schema.md, kinds `sweep_response@1` and `level_steps@1`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from rig_dsp import run, stimuli as st, sweep as sw  # noqa: E402

EQUIPMENT = "donner-eq-seeker"
OUT = REPO / "data" / "equipment" / EQUIPMENT / "measurements"
BANDS = ["31.25", "62.5", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]
BAND_HZ = [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

# Peak level each probe was sent at, by capture tag (the source project's
# `reamp.py --level`). The Seeker's ladder captures were sent at -30dBFS peak,
# so the five rungs left the computer at -70/-60/-50/-40/-30dBFS.
SEND_PEAK = {"ess_ladder_lad": -30.0, "ess_ladder_lad1018": -30.0, "ess": -23.0}


def flat(**over):
    s = {b: 0 for b in BANDS}
    s.update({k.replace("_", "."): v for k, v in over.items()})
    return s


def setting(bands=None, level=0, engaged=True):
    return {"engaged": engaged, "level_slider": level if engaged else None,
            "band_sliders": (bands if bands is not None else flat()) if engaged else None}


def one(band, n):
    s = flat()
    s[band] = n
    return s


def several(names, n):
    s = flat()
    for b in names:
        s[b] = n
    return s


# take id -> (settings, description)
TAKES = {
    "SEEK01": (setting(engaged=False), "bypass reference"),
    "SEEK02": (setting(), "engaged, every slider at 0: the flat reference"),
    **{f"SEEK{3 + i:02d}": (setting(one(b, +5)), f"{b}Hz slider at +5, others 0")
       for i, b in enumerate(BANDS)},
    "SEEK13": (setting(one("125", -5)), "125Hz at -5"),
    "SEEK14": (setting(one("1k", -5)), "1kHz at -5"),
    "SEEK15": (setting(several(["500", "1k", "2k"], -2)), "500/1k/2k at -2"),
    "SEEK16": (setting(several(["125", "250"], -5)), "125+250 at -5"),
    "SEEK17": (setting(several(BANDS, +2)), "all ten bands at +2"),
    "SEEK18": (setting(level=+5), "Level slider +5"),
    "SEEK19": (setting(level=-5), "Level slider -5"),
    "SEEK20": (setting(), "flat, levels probe (linearity reference)"),
    "SEEK21": (setting(one("500", -2)), "500Hz at -2 (taper)"),
    "SEEK22": (setting(one("500", +2)), "500Hz at +2 (taper)"),
    "SEEK23": (setting(one("125", +5)), "125Hz at +5, levels probe (boost compression)"),
    "SEEK24": (setting(several(["500", "1k", "2k"], -3)), "500/1k/2k at -3"),
    "SEEK25": (setting(several(["500", "1k", "2k"], -4)), "500/1k/2k at -4"),
    "SEEK27": (setting(several(["125", "250"], -2)), "125+250 at -2"),
    "SEEK28": (setting(several(["125", "250"], -3)), "125+250 at -3"),
    "SEEK29": (setting(several(["125", "250"], -4)), "125+250 at -4 (2026-10-18 session)"),
}

# capture tag -> reference capture for that tag
LADDER_REF = {"lad": ("SEEK02", "lad"), "lad1018": ("SEEK02", "lad1018")}
SESSION_REF = {"SEEK29": "lad1018"}       # takes measured against a later session's flat


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p: Path, root: Path) -> str:
    return p.relative_to(root).as_posix()


def r(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return None
    return round(float(x), nd)


def noise_block(rec, sr, layout):
    tail = sw.tail_noise(rec, sr, layout)
    if tail is None:
        return None
    from scipy import signal as sg
    b, a = sg.butter(4, [20, min(20000, sr / 2 * 0.95)], btype="band", fs=sr)
    bl = sg.filtfilt(b, a, tail)
    f, p = sg.welch(tail, sr, nperseg=min(8192, len(tail)))
    fo, db = sw.third_octave(f, 10 * np.log10(p * (f[1] - f[0]) * 1.5 + 1e-30),
                             np.ones_like(f, dtype=bool), lo=-17, hi=14)
    return {"seconds": r(len(tail) / sr, 2), "rms_dbfs_20_20k": r(sw.rms_dbfs(bl)),
            "third_octave_dbfs": [[r(x, 1), r(y)] for x, y in zip(fo, db)]}


def analyse_sweep(job):
    """One capture against its reference capture: legacy and Farina routes."""
    root = Path(job["root"])
    take_p, ref_p, probe = root / job["file"], root / job["ref_file"], job["probe"]
    rec, sr = sw.load(take_p)
    ref, sr2 = sw.load(ref_p)
    assert sr == sr2
    lt, lr = sw.locate(rec, sr, probe), sw.locate(ref, sr, probe)
    wt, nt = sw.welch_rungs(rec, sr, lt)
    wr, nr = sw.welch_rungs(ref, sr, lr)
    legacy = sw.welch_ratio(wt, wr, nt, nr)
    grid = sw.log_grid(20, 20000, 12)
    fund = 1000 * 2.0 ** (np.arange(-15, 3) / 3.0)            # 31.5Hz .. 1.6kHz
    send = job["send_peak"] if "send_peak" in job else SEND_PEAK.get(job["tag_key"])
    rungs = []
    levels = st.ESS_LADDER_LEVELS if probe == "ess_ladder" else (st.PROBE_PEAK_DBFS,)
    for i in range(lt.n_rungs):
        seg_t = rec[lt.starts[i]:lt.starts[i] + int(lt.sweep_seconds * sr)]
        seg_r = ref[lr.starts[i]:lr.starts[i] + int(lr.sweep_seconds * sr)]
        ft = sw.farina_rung(rec, sr, lt, i)
        fr = sw.farina_rung(ref, sr, lr, i)
        mag, ph = sw.smooth_complex(ft["f"], ft["H1"] / (fr["H1"] + 1e-30), grid)
        mag_ref = sw.smooth_complex(fr["f"], fr["H1"], grid)[0]
        # mask the Farina curve where the legacy route found no SNR
        leg = legacy[i]
        ok = np.ones_like(grid, dtype=bool)
        if leg is not None:
            fo, _, _ = leg
            lo_ok, hi_ok = (fo.min(), fo.max()) if len(fo) else (np.inf, -np.inf)
            ok = (grid >= lo_ok / 2 ** (1 / 6)) & (grid <= hi_ok * 2 ** (1 / 6))
        ok &= mag_ref > (mag_ref.max() - 50)
        harm = sw.harmonic_levels(ft, fund)
        rung = {
            "rung": i,
            "file_level_dbfs": levels[i] if probe == "ess_ladder" else st.PROBE_PEAK_DBFS,
            "send_peak_dbfs": (send - (levels[-1] - levels[i])) if (send is not None) else None,
            "return_peak_dbfs": r(sw.peak_dbfs(seg_t)),
            "reference_return_peak_dbfs": r(sw.peak_dbfs(seg_r)),
            "legacy_third_octave_db": None if leg is None else
                [[r(x, 1), r(y)] for x, y in zip(leg[0], leg[1])],
            "legacy_usable_pct_40_10k": None if leg is None else r(leg[2], 0),
            "farina_db": [r(m) if k else None for m, k in zip(mag, ok)],
            "farina_phase_deg": [r(np.degrees(p), 1) if k else None for p, k in zip(ph, ok)],
            "harmonics_db_rel_fundamental": {f"h{m}": [r(v, 1) for v in vals]
                                             for m, vals in harm.items()},
        }
        rungs.append(rung)
    return {
        "key": job["key"], "take_id": job["take_id"],
        "capture": {
            "file": job["file"], "sha256": sha256(take_p), "sample_rate": sr,
            "probe": probe, "tag": job["tag"],
            "recorded": datetime.fromtimestamp(take_p.stat().st_mtime).strftime("%Y-%m-%d"),
            "duration_s": r(len(rec) / sr, 2),
            "superseded": job.get("superseded"),
        },
        "reference": {"take_id": job["ref_take"], "file": job["ref_file"], "sha256": sha256(ref_p)},
        "farina_grid_hz": [r(g, 2) for g in grid],
        "harmonic_fundamentals_hz": [r(f, 1) for f in fund],
        "rungs": rungs,
        "noise": noise_block(rec, sr, lt),
        "reference_noise": noise_block(ref, sr, lr),
    }


def analyse_levels(job):
    """Level-steps probe: fundamental and harmonics of each 110Hz step."""
    root = Path(job["root"])
    p = root / job["file"]
    rec, sr = sw.load(p)
    probe = st.level_steps(sr=sr) * 10 ** (st.PROBE_PEAK_DBFS / 20.0)
    n = min(len(rec), len(probe) + 4 * sr)
    size = 1 << int(np.ceil(np.log2(n + len(probe))))
    corr = np.fft.irfft(np.fft.rfft(rec[:n], size) * np.conj(np.fft.rfft(probe, size)), size)
    start = int(np.argmax(np.abs(corr[:max(n - len(probe) + 1, 1)])))
    step, gap = int(st.LEVELS_STEP_SEC * sr), int(st.LEVELS_GAP_SEC * sr)
    steps = []
    for k, db in enumerate(st.LEVELS_DB):
        a = start + gap + k * (step + gap) + int(0.25 * sr)
        seg = rec[a:a + sr]                       # middle 1.0s of the 1.5s step
        w = np.hanning(len(seg))
        spec = np.abs(np.fft.rfft(seg * w)) * 2 / np.sum(w)
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        amp = [float(spec[int(np.argmin(np.abs(f - st.LEVELS_HZ * m)))]) for m in range(1, 6)]
        thd = np.sqrt(sum(a_ ** 2 for a_ in amp[1:])) / (amp[0] + 1e-30)
        steps.append({
            "step": k, "file_level_dbfs": r(db + st.PROBE_PEAK_DBFS, 1),
            "fundamental_dbfs_peak": r(20 * np.log10(amp[0] + 1e-30)),
            "harmonics_db_rel_fundamental": {f"h{m + 1}": r(20 * np.log10(amp[m] / (amp[0] + 1e-30)), 1)
                                             for m in range(1, 5)},
            "thd_pct_h2_h5": r(100 * thd, 3),
        })
    return {"key": job["key"], "take_id": job["take_id"],
            "capture": {"file": job["file"], "sha256": sha256(p), "sample_rate": sr,
                        "probe": "levels", "tag": None,
                        "recorded": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d"),
                        "duration_s": r(len(rec) / sr, 2)},
            "steps": steps}


def jobs_for(root: Path):
    reamps = root / "reamps"
    jobs = []
    for tid in TAKES:
        for p in sorted(reamps.glob(f"{tid}_*.wav")):
            stem = p.stem[len(tid) + 1:]
            base = {"root": str(root), "take_id": tid, "file": rel(p, root), "key": f"{tid}:{stem}"}
            if stem.startswith("ess_ladder"):
                tag = stem[len("ess_ladder_"):] if stem != "ess_ladder" else ""
                ref_tag = SESSION_REF.get(tid, tag)
                ref_file = rel(reamps / f"SEEK02_ess_ladder_{ref_tag}.wav", root)
                ref_take = "SEEK02"
                if tid == "SEEK02" and tag == "lad":
                    continue          # the reference itself; described by its lad1018 pairing
                if tid == "SEEK02" and tag == "lad1018":
                    ref_file = rel(reamps / "SEEK02_ess_ladder_lad.wav", root)
                jobs.append({**base, "kind": "sweep", "probe": "ess_ladder", "tag": tag,
                             "tag_key": f"ess_ladder_{tag}", "ref_file": ref_file, "ref_take": ref_take})
            elif stem in ("ess", "ess_lin"):
                if tid == "SEEK01":
                    ref_file, ref_take = rel(reamps / "SEEK02_ess.wav", root), "SEEK02"
                elif tid == "SEEK02" and stem == "ess":
                    ref_file, ref_take = rel(reamps / "SEEK01_ess.wav", root), "SEEK01"
                elif tid == "SEEK02":
                    continue
                else:
                    ref_file, ref_take = rel(reamps / f"SEEK02_{stem}.wav", root), "SEEK02"
                has_ladder = (reamps / f"{tid}_ess_ladder_lad.wav").exists()
                jobs.append({**base, "kind": "sweep", "probe": "ess", "tag": stem[4:] or None,
                             "tag_key": stem, "ref_file": ref_file, "ref_take": ref_take,
                             "superseded": ("single-level capture; the ess_ladder capture of this "
                                            "take supersedes it") if has_ladder else None})
            elif stem == "levels":
                jobs.append({**base, "kind": "levels"})
    return jobs


def work(job):
    return analyse_sweep(job) if job["kind"] == "sweep" else analyse_levels(job)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audio-root", type=Path,
                    default=Path(os.environ.get("RIG_AUDIO_ROOT", ".")),
                    help="folder that contains reamps/")
    ap.add_argument("--workers", type=int, default=None)
    args = ap.parse_args()
    root = args.audio_root.resolve()
    jobs = jobs_for(root)
    if not jobs:
        sys.exit(f"no SEEK captures under {root / 'reamps'}")
    run.pin_blas()
    n = run.workers(1.0, jobs=len(jobs), requested=args.workers, name="export_eq_seeker")
    results = {}
    with run.Progress(total=len(jobs), name="export_eq_seeker") as prog, \
            ProcessPoolExecutor(max_workers=n) as ex:
        futs = {ex.submit(work, j): j for j in jobs}
        for fu in as_completed(futs):
            res = fu.result()
            results[res["key"]] = res
            prog.step(note=res["key"])

    OUT.mkdir(parents=True, exist_ok=True)
    for tid, (settings, desc) in TAKES.items():
        caps = [v for k, v in sorted(results.items()) if v["take_id"] == tid]
        doc = {
            "schema": "rig-equipment/take@1",
            "equipment": EQUIPMENT,
            "take_id": tid,
            "description": desc,
            "settings": settings,
            "captures": [{k: v for k, v in c.items() if k not in ("key", "take_id")}
                         for c in caps],
        }
        if tid == "SEEK02":
            doc["note"] = ("SEEK02 is the flat reference for every other take. Its own captures "
                           "are analysed against SEEK01 (bypass: insertion response) and against "
                           "the 2026-10-18 re-recording (session drift).")
        (OUT / f"{tid}.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print(f"wrote {len(TAKES)} take files to {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
