#!/usr/bin/env python3
"""
Fit and validate the NR300 expander model from ../../measurements/envelopes.npz.

    python fit.py

Procedure (unchanged from the source project's nr300_model.py):

1. `floor` is read straight off the level-steps captures: the median of every
   fully gated step on NR05/NR06. The music cannot identify it, because a gated
   frame there sits within a few dB of the loop noise.
2. Settled (NR02) fits every other parameter on the FIRST half of the music and
   is scored on the second half, which it never saw. Both detectors (rms,
   peak) are fitted, with the floor free and from the ladder.
3. Published: floor from the ladder; detector by held-out music error. A tie
   (within 0.05dB) is broken by the level-steps error on NR04-NR06.
4. The other six settings keep every shape parameter from the settled fit and
   refit ONLY the one parameter their knob moves (thr, or release_ms).
5. Every setting is then scored, with no refit, on its level-steps capture.

The re-amp loop adds about -97dBFS of noise after the gate, which the gate
cannot touch. That is a nuisance parameter (`noise_db`), used only to predict
the captured envelope. Rest frames (input below -85dBFS) are excluded from
the fit, because there the input frame is itself mostly loop noise.
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

from model import gain_db  # noqa: E402
from rig_dsp import run  # noqa: E402
from rig_dsp.envelope import from_cdb  # noqa: E402

NPZ = HERE.parents[1] / "measurements" / "envelopes.npz"
SETTLED = "NR02"
TAKES = {"NR02": None, "NR03": "thr", "NR04": "thr", "NR05": "thr", "NR06": "thr",
         "NR07": "release_ms", "NR08": "release_ms"}
MUSIC_DB, REST_DB = -60.0, -85.0
SHAPE = ("hyst", "floor", "slope", "det_ms", "attack_ms", "hold_ms", "makeup", "noise_db")
BOUNDS = {"thr": (-100, -15), "hyst": (0, 20), "floor": (-40, 0), "slope": (0.05, 20),
          "det_ms": (0.1, 100), "attack_ms": (0.05, 50), "release_ms": (1, 2000),
          "hold_ms": (0, 300), "makeup": (-3, 3), "noise_db": (-110, -80)}


class Env:
    def __init__(self, z, take, probe, s=slice(None)):
        g = lambda k: from_cdb(z[f"{take}/{probe}/{k}"])[s]  # noqa: E731
        self.x, self.y = g("x_rms"), g("y_rms")
        self.det = {"rms": g("key_rms"), "peak": g("key_peak")}


def predict_env(E, p):
    out = E.x + gain_db(E.det[p["detector"]], p)
    return 10 * np.log10(10 ** (out / 10) + 10 ** (p["noise_db"] / 10))


def errors(E, p):
    d = predict_env(E, p) - E.y
    cls = {"fit": E.x > REST_DB, "music": E.x > MUSIC_DB,
           "transition": (E.x <= MUSIC_DB) & (E.x > REST_DB), "rest": E.x <= REST_DB}
    return {k: round(float(np.sqrt(np.mean(d[s] ** 2))), 3) if s.any() else None
            for k, s in cls.items()}


def fit_params(E, p0, names):
    lo = np.array([BOUNDS[k][0] for k in names], float)
    hi = np.array([BOUNDS[k][1] for k in names], float)
    mask = E.x > REST_DB

    def resid(th):
        return (predict_env(E, dict(p0, **dict(zip(names, th)))) - E.y)[mask]

    starts = [p0]
    if "thr" in names:
        starts = [dict(p0, thr=t) for t in (-85.0, -75.0, -65.0, -55.0, -45.0, -35.0, -25.0)]
    best = None
    for s in starts:
        x0 = np.clip(np.array([s[k] for k in names], float), lo + 1e-6, hi - 1e-6)
        r = least_squares(resid, x0, bounds=(lo, hi), diff_step=0.02,
                          loss="soft_l1", f_scale=3.0, max_nfev=600)
        c = float(np.sqrt(np.mean(resid(r.x) ** 2)))
        if best is None or c < best[0]:
            best = (c, r.x)
    return dict(p0, **{k: float(v) for k, v in zip(names, best[1])})


def fit_settled(E, detector, floor=None):
    names = ["thr", "release_ms"] + [k for k in SHAPE if not (k == "floor" and floor is not None)]
    best = None
    for rel0 in (20.0, 100.0, 400.0):
        for hold0 in (5.0, 50.0):
            for sl0 in (1.0, 5.0):
                p0 = dict(detector=detector, thr=-65.0, release_ms=rel0, hyst=3.0,
                          floor=-17.0 if floor is None else floor, slope=sl0, det_ms=10.0,
                          attack_ms=1.0, hold_ms=hold0, makeup=-0.2, noise_db=-95.0)
                p = fit_params(E, p0, names)
                e = errors(E, p)["fit"]
                if best is None or e < best[0]:
                    best = (e, p)
    return best[1]


def fit_knob(E, p_settled, knob):
    if knob == "thr":
        return fit_params(E, p_settled, [knob])
    best = None
    for r0 in (5.0, 50.0, 300.0, 1500.0):
        p = fit_params(E, dict(p_settled, release_ms=r0), [knob])
        e = errors(E, p)["fit"]
        if best is None or e < best[0]:
            best = (e, p)
    return best[1]


def ladder_steps(E, pred):
    on = E.x > E.x.max() - 45
    runs, s0 = [], None
    for i, v in enumerate(on):
        if v and s0 is None:
            s0 = i
        elif not v and s0 is not None:
            if i - s0 > 150:
                runs.append((s0, i))
            s0 = None
    real, model = [], []
    for s, f_ in runs:
        core = slice(s + 60, f_ - 40)
        real.append(round(float(np.median(E.y[core] - E.x[core])), 2))
        model.append(round(float(np.median(pred[core] - E.x[core])), 2))
    return real, model


def variant(args):
    """One settled variant, then the knob refits and level-steps scoring."""
    det, floor = args
    z = np.load(NPZ)
    E = Env(z, SETTLED, "music")
    half = len(E.x) // 2
    first, second = Env(z, SETTLED, "music", slice(0, half)), Env(z, SETTLED, "music",
                                                                  slice(half, None))
    ph, pf = fit_settled(first, det, floor), fit_settled(E, det, floor)
    per = {}
    steps = []
    for t, par in TAKES.items():
        Et, Lt = Env(z, t, "music"), Env(z, t, "levels")
        q = pf if par is None else fit_knob(Et, pf, par)
        real, model = ladder_steps(Lt, predict_env(Lt, q))
        srms = float(np.sqrt(np.mean(np.subtract(real, model) ** 2)))
        per[t] = {"params": q, "music_error_db": errors(Et, q),
                  "music_error_without_refit_db": errors(Et, pf)["fit"],
                  "levels": {"step_gain_real_db": real, "step_gain_model_db": model,
                             "step_rms_db": round(srms, 3)}}
        if t in ("NR04", "NR05", "NR06"):
            steps.append(srms)
    return {"name": f"{det}/floor-{'ladder' if floor is not None else 'free'}",
            "params_first_half": ph, "params_full": pf,
            "err_first_half": errors(first, ph), "err_second_half_heldout": errors(second, ph),
            "ladder_step_rms_NR04_06": round(float(np.mean(steps)), 3), "per_take": per}


def main():
    z = np.load(NPZ)
    gated = []
    for t in ("NR05", "NR06"):
        L = Env(z, t, "levels")
        gated += [v for v in ladder_steps(L, L.y)[0] if v < -12]
    floor = float(np.median(gated))
    jobs = [(d, f) for d in ("rms", "peak") for f in (None, floor)]
    run.pin_blas()
    n = run.workers(0.6, jobs=len(jobs), name="fit_nr300")
    with run.Progress(total=len(jobs), name="fit_nr300") as prog, \
            ProcessPoolExecutor(max_workers=n) as ex:
        variants = {}
        for v in ex.map(variant, jobs):
            variants[v["name"]] = v
            prog.step(note=v["name"])

    anchored = {k: v for k, v in variants.items() if k.endswith("ladder")}
    best = min(v["err_second_half_heldout"]["fit"] for v in anchored.values())
    tied = {k: v for k, v in anchored.items() if v["err_second_half_heldout"]["fit"] - best < 0.05}
    pub = min(tied, key=lambda k: tied[k]["ladder_step_rms_NR04_06"])
    V = variants[pub]
    params = {
        "schema": "rig-equipment/model-params@1", "equipment": "behringer-nr300",
        "model": "expander", "published_variant": pub, "floor_from_level_steps_db": floor,
        "level_scale": "dBFS at the capture; played bass peaks -14.0dBFS, RMS -33.2dBFS",
        "per_take": {t: {"params": V["per_take"][t]["params"]} for t in TAKES},
    }
    validation = {"published_variant": pub, "tied_on_heldout_music": list(tied),
                  "error_classes": {"fit": "input frame > -85dBFS", "music": "> -60",
                                    "transition": "-85 to -60", "rest": "<= -85 (not fitted)"},
                  "variants": {k: {kk: vv for kk, vv in v.items() if kk not in ("name",)}
                               for k, v in variants.items()}}
    (HERE / "params.json").write_text(json.dumps(params, indent=1), encoding="utf-8")
    (HERE / "validation.json").write_text(json.dumps(validation, indent=1), encoding="utf-8")

    print(f"\nfloor from level steps {floor:+.2f}dB; published {pub}")
    for k, v in variants.items():
        q = v["params_full"]
        print(f"  {k:<18} held-out music fit {v['err_second_half_heldout']['fit']:.2f} "
              f"music {v['err_second_half_heldout']['music']:.2f}  steps {v['ladder_step_rms_NR04_06']:.2f}"
              f"  thr {q['thr']:.1f} floor {q['floor']:.1f} slope {q['slope']:.2f}")
    for t in TAKES:
        r = V["per_take"][t]
        par = TAKES[t]
        print(f"  {t} {par or 'settled':<11} {('' if par is None else f'{r['params'][par]:8.1f}'):>8}"
              f"  music fit {r['music_error_db']['fit']:.2f}  steps {r['levels']['step_rms_db']:.2f}")


if __name__ == "__main__":
    main()
