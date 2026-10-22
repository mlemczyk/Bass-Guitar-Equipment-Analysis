#!/usr/bin/env python3
"""
Fit and validate the Seeker model against ../../measurements/*.json.

    python fit.py

Fits two forms with the same parameters (per band f0, Q, K; one shared slider
taper):
  * ratio   -- every band in one feedback network (model.py's default)
  * cascade -- independent bands, effects add in dB
then refits each with every combination take left out in turn and predicts it.
Writes params.json (the ratio form, fitted on everything) and validation.json.

Fitted on the small-signal response: the mean of ladder rungs 0-2 (sent at
-70/-60/-50dBFS peak). Rungs 3-4 reach the re-amp loop's own distortion region
when a band is boosted; see ../../findings.md.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from model import BANDS, SeekerModel  # noqa: E402
from rig_dsp import run  # noqa: E402

MEAS = HERE.parents[1] / "measurements"
NOMINAL = np.array([31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000])
F_LO, F_HI = 25.0, 18000.0
SINGLES = ["SEEK03", "SEEK04", "SEEK05", "SEEK06", "SEEK07", "SEEK08", "SEEK09", "SEEK10",
           "SEEK11", "SEEK12", "SEEK13", "SEEK14", "SEEK21", "SEEK22"]
COMBOS = ["SEEK15", "SEEK16", "SEEK17", "SEEK24", "SEEK25", "SEEK27", "SEEK28", "SEEK29"]


def load_take(tid):
    d = json.loads((MEAS / f"{tid}.json").read_text(encoding="utf-8"))
    caps = d["captures"]
    lad = [c for c in caps if c["capture"]["probe"] == "ess_ladder"]
    if lad:
        c, rungs = lad[0], lad[0]["rungs"][:3]
    else:                                   # SEEK13/14: single-level cuts only
        c = [c for c in caps if c["capture"]["probe"] == "ess" and c["capture"]["tag"] is None][0]
        rungs = c["rungs"][:1]
    f = np.array(c["farina_grid_hz"])
    mag = np.array([[np.nan if v is None else v for v in r["farina_db"]] for r in rungs])
    ph = np.array([[np.nan if v is None else v for v in r["farina_phase_deg"]] for r in rungs])
    m = np.nanmean(mag, axis=0)
    p = np.nanmean(ph, axis=0)
    ok = np.isfinite(m) & (f >= F_LO) & (f <= F_HI)
    return {"take": tid, "sliders": d["settings"]["band_sliders"], "f": f[ok], "db": m[ok],
            "phase": p[ok], "capture": c["capture"]["file"]}


N_INC = 10                     # u(-5)..u(+5) as 10 positive increments, last fixed


def unpack(p):
    f0 = NOMINAL * np.exp(p[0:10])
    q = np.exp(p[10:20])
    k = np.exp(p[20:30])
    inc = np.log1p(np.exp(np.concatenate([p[30:30 + N_INC - 1], [0.0]])))
    law = np.concatenate([[0.0], np.cumsum(inc) / np.sum(inc)])
    return SeekerModel(f0, q, k, law, {0: 0.0})


def law_params(law):
    """Inverse of unpack's law parametrisation (last increment fixed at softplus(0))."""
    inc = np.diff(np.asarray(law, dtype=float))
    inc = inc / inc[-1] * np.log(2.0)
    return np.log(np.expm1(np.maximum(inc, 1e-6)))[:-1]


# Two starting slider laws: a centred slider loading the network by half
# (a textbook linear pot) and by very little.
STARTS = {"linear": np.linspace(0, 1, 11),
          "light_centre": np.array([0, .005, .01, .02, .03, .04, .15, .3, .5, .75, 1.0])}


def residuals(p, data, cascade):
    m = unpack(p)
    out = []
    for d in data:
        H = m.response(d["f"], d["sliders"], cascade=cascade)
        out.append(20 * np.log10(np.abs(H)) - d["db"])
    return np.concatenate(out)


def fit(data, cascade):
    """Best of the STARTS by final cost."""
    lo = np.concatenate([np.full(10, -0.4), np.full(10, np.log(0.2)), np.full(10, np.log(0.5)),
                         np.full(N_INC - 1, -12)])
    hi = np.concatenate([np.full(10, 0.4), np.full(10, np.log(5)), np.full(10, np.log(200)),
                         np.full(N_INC - 1, 12)])
    best = None
    for law in STARTS.values():
        p0 = np.concatenate([np.zeros(10), np.zeros(10), np.full(10, np.log(4.0)),
                             np.clip(law_params(law), -11.9, 11.9)])
        res = least_squares(residuals, p0, bounds=(lo, hi), args=(data, cascade),
                            x_scale="jac", max_nfev=6000)
        if best is None or res.cost < best.cost:
            best = res
    return best.x


def take_error(m, d, cascade):
    H = m.response(d["f"], d["sliders"], cascade=cascade)
    e = 20 * np.log10(np.abs(H)) - d["db"]
    band = (d["f"] >= 40) & (d["f"] <= 10000)
    ph_model = np.degrees(np.unwrap(np.angle(H)))
    ph_err = ph_model - d["phase"]
    ph_err -= np.nanmedian(ph_err[band])      # a constant offset is not information here
    return {"rms_db": round(float(np.sqrt(np.mean(e[band] ** 2))), 2),
            "worst_db": round(float(e[band][np.argmax(np.abs(e[band]))]), 2),
            "phase_rms_deg": round(float(np.sqrt(np.nanmean(ph_err[band] ** 2))), 1)}


def job(args):
    form, leave_out, data = args
    train = [d for d in data if d["take"] != leave_out]
    return form, leave_out, fit(train, form == "cascade")


def main():
    data = [load_take(t) for t in SINGLES + COMBOS]
    jobs = [(form, lo, data) for form in ("ratio", "cascade") for lo in [None] + COMBOS]
    run.pin_blas()
    n = run.workers(0.5, jobs=len(jobs), name="fit_seeker_model")
    fits = {}
    with run.Progress(total=len(jobs), name="fit_seeker_model") as prog, \
            ProcessPoolExecutor(max_workers=n) as ex:
        for form, lo, p in ex.map(job, jobs):
            fits[(form, lo)] = p
            prog.step(note=f"{form} without {lo}")

    validation = {"fit_band_hz": [40, 10000], "forms": {}}
    for form in ("ratio", "cascade"):
        full = unpack(fits[(form, None)])
        rows = {d["take"]: take_error(full, d, form == "cascade") for d in data}
        loo = {}
        for t in COMBOS:
            m = unpack(fits[(form, t)])
            d = [x for x in data if x["take"] == t][0]
            loo[t] = take_error(m, d, form == "cascade")
        validation["forms"][form] = {
            "in_sample": rows,
            "leave_one_out_combos": loo,
            "in_sample_rms_singles_db": round(float(np.sqrt(np.mean(
                [rows[t]["rms_db"] ** 2 for t in SINGLES]))), 2),
            "in_sample_rms_combos_db": round(float(np.sqrt(np.mean(
                [rows[t]["rms_db"] ** 2 for t in COMBOS]))), 2),
            "loo_rms_combos_db": round(float(np.sqrt(np.mean(
                [loo[t]["rms_db"] ** 2 for t in COMBOS]))), 2),
        }

    level, insertion = level_and_insertion()

    def form_params(form):
        m = unpack(fits[(form, None)])
        return {
            "bands": {b: {"f0_hz": round(float(m.f0[i]), 2), "q": round(float(m.q[i]), 3),
                          "k": round(float(m.k[i]), 4)} for i, b in enumerate(BANDS)},
            "slider_law_by_notch": [round(float(v), 5) for v in m.law],
            "loo_rms_combos_db": validation["forms"][form]["loo_rms_combos_db"],
        }

    loo = {f: validation["forms"][f]["loo_rms_combos_db"] for f in ("ratio", "cascade")}
    params = {
        "schema": "rig-equipment/model-params@1",
        "equipment": "donner-eq-seeker",
        "model": "graphic_eq_ratio",
        "reference_state": "engaged, every slider 0, Level 0",
        "fitted_on": SINGLES + COMBOS,
        "default_form": min(loo, key=loo.get),
        "slider_law_notches": list(range(-5, 6)),
        "slider_law_identified_at": [-5, -4, -3, -2, 0, 2, 5],
        "forms": {f: form_params(f) for f in ("cascade", "ratio")},
        "level_slider_db": level,
        "insertion_vs_bypass": insertion,
    }
    (HERE / "params.json").write_text(json.dumps(params, indent=1), encoding="utf-8")
    (HERE / "validation.json").write_text(json.dumps(validation, indent=1), encoding="utf-8")

    for form, v in validation["forms"].items():
        print(f"\n{form}: singles {v['in_sample_rms_singles_db']}dB, combos in-sample "
              f"{v['in_sample_rms_combos_db']}dB, combos left out {v['loo_rms_combos_db']}dB")
        for t in COMBOS:
            print(f"   {t}  in {v['in_sample'][t]['rms_db']:5.2f}  out "
                  f"{v['leave_one_out_combos'][t]['rms_db']:5.2f}  "
                  f"phase {v['in_sample'][t]['phase_rms_deg']:5.1f} deg")
    print(f"\ndefault form: {params['default_form']}")
    for form, fp in params["forms"].items():
        print(f"{form} slider law u(-5..+5): {fp['slider_law_by_notch']}")
        for b, v in fp["bands"].items():
            print(f"  {b:>6} f0 {v['f0_hz']:8.1f}  Q {v['q']:.2f}  K {v['k']:.2f}")
    m = SeekerModel.load(HERE / "params.json")
    grid = [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    print("\nsingle band at +5, model gain at its nominal centre (default form):")
    print("  " + "  ".join(f"{b}:{20*np.log10(abs(m.response([g], {b: 5})[0])):+.1f}"
                           for b, g in zip(BANDS, grid)))


def level_and_insertion():
    """Level slider points; insertion from SEEK02 vs SEEK01."""
    def mean_db(tid, probe="ess"):
        d = json.loads((MEAS / f"{tid}.json").read_text(encoding="utf-8"))
        c = [c for c in d["captures"] if c["capture"]["probe"] == probe
             and c["capture"]["tag"] is None][0]
        f = np.array(c["farina_grid_hz"])
        m = np.array([np.nan if v is None else v for v in c["rungs"][0]["farina_db"]])
        return f, m, c

    # -5 from SEEK19 (a cut, so clear of the loop's distortion region). +2..+4
    # are loudness steps between full-chain re-amps of a played take in the
    # source project (+2: BK04 -> BK05; +3/+4: PL03/PL04, against Level 0), so
    # approximate. +5 is left out: PL05 read +14.2dB while already compressing,
    # and SEEK18 read +5.3dB from a single-level boost that returned inside the
    # loop's distortion region. See findings.md.
    f, m, _ = mean_db("SEEK19")
    band = (f >= 100) & (f <= 5000)
    level = {"-5": round(float(np.nanmean(m[band])), 2), "0": 0.0, "2": 6.0,
             "3": 7.0, "4": 9.0}
    f, m, _ = mean_db("SEEK02")
    keep = np.isfinite(m) & (f >= 20) & (f <= 20000)
    ins = {"f_hz": [round(float(x), 1) for x in f[keep][::4]],
           "db": [round(float(x), 2) for x in m[keep][::4]],
           "source": "SEEK02 (engaged flat) vs SEEK01 (bypassed), single-level ess"}
    return dict(sorted(level.items(), key=lambda kv: int(kv[0]))), ins


if __name__ == "__main__":
    main()
