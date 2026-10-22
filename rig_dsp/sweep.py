"""
Frequency response, linearity, harmonics and noise from re-amped sweep captures.

Two routes to the same magnitude, kept side by side on purpose:

* `welch_rungs()` is the **legacy route** the source project used for every
  published number (Welch PSD of each sweep, take divided by reference,
  third-octave means, SNR mask). It has no phase. It is kept so the numbers in
  `findings.md` can be reproduced exactly.
* `farina_rungs()` is the **Farina route**: deconvolve with the matched inverse
  filter, window the linear impulse response and each harmonic order. It gives
  magnitude *and* phase, and the harmonic orders, and is what the models in
  this dataset are fitted to.

Every response is a ratio of a take against a reference take captured through
the same loop, so the loop's own response divides out.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import soundfile as sf
from scipy import signal as sg

from . import stimuli as st

SNR_MARGIN_DB = 10.0
WELCH_NPERSEG = 16384


def load(path) -> tuple[np.ndarray, int]:
    y, sr = sf.read(str(path), dtype="float64", always_2d=True)
    return y.mean(axis=1), sr


def rms_dbfs(x) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-20))


def peak_dbfs(x) -> float:
    return float(20 * np.log10(np.max(np.abs(x)) + 1e-20))


# ---------------------------------------------------------------- locating

@dataclass
class Layout:
    """Where the sweeps sit inside a capture."""
    sweep_seconds: float
    n_rungs: int
    stride: int               # samples between rung starts
    starts: list[int]         # sample index of each rung's start
    stimulus_end: int         # sample after which only noise remains


def _first_match(rec, ref, window):
    seg = rec[:min(len(rec), window)]
    size = 1 << int(np.ceil(np.log2(len(seg) + len(ref))))
    corr = np.fft.irfft(np.fft.rfft(seg, size) * np.conj(np.fft.rfft(ref, size)), size)
    span = max(len(seg) - len(ref) + 1, 1)
    return int(np.argmax(np.abs(corr[:span])))


def locate(rec, sr, probe: str) -> Layout:
    """Find the sweep(s) in a capture of `ess_ladder` or `ess`.

    The search for the first rung is limited to where it can be, because
    correlating against the whole ladder would lock onto the loudest rung."""
    if probe == "ess_ladder":
        secs, n = st.ESS_LADDER_SECONDS, len(st.ESS_LADDER_LEVELS)
        ref, _ = st.exponential_sweep(seconds=secs, sr=sr)
        start = _first_match(rec, ref, int((st.ESS_LADDER_LEAD + secs + 4.0) * sr))
        stride = int((secs + st.ESS_LADDER_GAP) * sr)
    elif probe == "ess":
        secs, n = st.SWEEP_SECONDS, 1
        ref, _ = st.exponential_sweep(seconds=secs, sr=sr)
        start = _first_match(rec, ref, len(rec))
        stride = 0
    else:
        raise ValueError(probe)
    starts = [start + i * stride for i in range(n)]
    end = starts[-1] + len(ref) + int(0.25 * sr)       # 250ms guard for the IR tail
    return Layout(secs, n, stride, starts, end)


def tail_noise(rec, sr, layout: Layout, seconds=1.0):
    """The capture after every sweep has ended: the noise floor of the loop with
    the stage in it, at the settings of the take. None if the capture stops too
    soon after the last sweep."""
    tail = rec[layout.stimulus_end:]
    if len(tail) < int(0.5 * sr):
        return None
    return tail[-int(seconds * sr):] if len(tail) > int(seconds * sr) else tail


# ---------------------------------------------------------------- legacy route

def third_octave(f, db, valid, lo=-18, hi=15):
    centres = 1000 * 2.0 ** (np.arange(lo, hi) / 3.0)
    fo, do = [], []
    for fc in centres:
        m = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6)) & valid
        if m.any():
            fo.append(fc)
            do.append(float(np.mean(db[m])))
    return np.array(fo), np.array(do)


def welch_rungs(rec, sr, layout: Layout):
    """Per rung: (f, psd_db). Plus the tail-noise PSD on the same grid."""
    ref, _ = st.exponential_sweep(seconds=layout.sweep_seconds, sr=sr)
    out = []
    for a in layout.starts:
        seg = rec[a:a + len(ref)]
        if len(seg) < len(ref) * 0.9:
            out.append(None)
            continue
        f, pxx = sg.welch(seg, sr, nperseg=WELCH_NPERSEG)
        out.append((f, 10 * np.log10(pxx + 1e-20)))
    tail = tail_noise(rec, sr, layout)
    noise = None
    if tail is not None and len(tail) > 8192:
        fn, pn = sg.welch(tail, sr, nperseg=8192)
        noise = np.interp(out[0][0], fn, pn) if out[0] is not None else None
    return out, noise


def welch_ratio(take, ref, take_noise, ref_noise):
    """Third-octave take/ref ratio per rung, masked where either capture is
    within SNR_MARGIN_DB of its own noise floor. Returns per rung
    (centres, gain_db, usable_pct) or None."""
    res = []
    for a, b in zip(take, ref):
        if a is None or b is None:
            res.append(None)
            continue
        f, da = a
        _, db_ = b
        ok = np.ones_like(da, dtype=bool)
        for psd, nz in ((da, take_noise), (db_, ref_noise)):
            if nz is not None:
                ok &= psd > (10 * np.log10(nz + 1e-20) + SNR_MARGIN_DB)
        ok &= db_ > (db_.max() - 50)
        band = (f >= 40) & (f <= 10000)
        usable = 100.0 * np.sum(ok & band) / max(np.sum(band), 1)
        fo, g = third_octave(f, da - db_, ok)
        res.append((fo, g, usable))
    return res


# ---------------------------------------------------------------- Farina route

PRE_S, POST_S = 0.05, 0.60        # linear-IR window around the impulse


def harmonic_offset_s(order, sweep_seconds):
    return sweep_seconds * np.log(order) / np.log(st.F_END / st.F_START)


def _window(n_pre, n_post):
    w = np.ones(n_pre + n_post)
    k = max(n_pre // 2, 1)
    w[:k] = 0.5 * (1 - np.cos(np.linspace(0, np.pi, k)))
    k2 = max(n_post // 4, 1)
    w[-k2:] = 0.5 * (1 + np.cos(np.linspace(0, np.pi, k2)))
    return w


def farina_rung(rec, sr, layout: Layout, rung: int, max_order=5, nfft=1 << 16):
    """Linear transfer and harmonic orders of one sweep, by deconvolution.

    Returns dict with `f`, `H1` (complex, linear order) and `Hm` {order: complex
    spectrum of that order's impulse response}. Absolute: includes the loop and
    the probe level; divide by a reference to remove both."""
    sweep, inv = st.exponential_sweep(seconds=layout.sweep_seconds, sr=sr)
    a = layout.starts[rung]
    seg = rec[a:a + len(sweep) + int(1.0 * sr)]
    n = 1 << int(np.ceil(np.log2(len(seg) + len(inv))))
    ir = np.fft.irfft(np.fft.rfft(seg, n) * np.fft.rfft(inv, n), n)
    # Unnormalised: only ratios against a reference capture are ever used.
    # Each order is rolled so its impulse sits at t=0, so phase excludes the
    # bulk loop latency.
    lin = int(np.argmax(np.abs(ir)))
    f = np.fft.rfftfreq(nfft, 1 / sr)
    out = {"f": f, "Hm": {}, "lin_index": lin}
    pre, post = int(PRE_S * sr), int(POST_S * sr)
    w = _window(pre, post)
    seg1 = ir[lin - pre:lin + post] * w
    out["H1"] = np.fft.rfft(np.roll(np.pad(seg1, (0, nfft - len(seg1))), -pre), nfft)
    # harmonic orders: short symmetric windows, half the gap to the next order
    for m in range(2, max_order + 1):
        c = lin - int(harmonic_offset_s(m, layout.sweep_seconds) * sr)
        gap = int((harmonic_offset_s(m + 1, layout.sweep_seconds)
                   - harmonic_offset_s(m, layout.sweep_seconds)) * sr)
        half = max(min(gap // 2, int(0.08 * sr)), 64)
        lo, hi = c - half, c + half
        if lo < 0:
            continue
        wm = ir[lo:hi] * np.hanning(hi - lo)
        out["Hm"][m] = np.fft.rfft(np.roll(np.pad(wm, (0, nfft - len(wm))), -half), nfft)
    return out


def log_grid(f_lo=20.0, f_hi=20000.0, per_octave=12):
    n = int(np.floor(np.log2(f_hi / f_lo) * per_octave)) + 1
    return f_lo * 2.0 ** (np.arange(n) / per_octave)


def smooth_complex(f, H, grid, frac=12):
    """Fractional-octave smoothing of a complex response onto `grid`:
    magnitude by power mean, phase from the complex mean."""
    mag, ph = [], []
    for fc in grid:
        m = (f >= fc * 2 ** (-0.5 / frac)) & (f < fc * 2 ** (0.5 / frac))
        if not m.any():
            i = int(np.argmin(np.abs(f - fc)))
            m = np.zeros_like(f, dtype=bool)
            m[i] = True
        mag.append(10 * np.log10(np.mean(np.abs(H[m]) ** 2) + 1e-30))
        ph.append(np.angle(np.mean(H[m])))
    return np.array(mag), np.unwrap(np.array(ph))


def harmonic_levels(take, grid_fund):
    """Level of each harmonic order relative to the linear order, at each
    fundamental frequency in `grid_fund` (Hz). Order m at fundamental f lives
    at output frequency m*f in that order's spectrum."""
    f, H1 = take["f"], take["H1"]
    out = {}
    for m, Hm in take["Hm"].items():
        vals = []
        for f0 in grid_fund:
            if m * f0 > f[-1] * 0.95:
                vals.append(None)
                continue
            a1 = np.abs(np.interp(f0, f, np.abs(H1)))
            am = np.abs(np.interp(m * f0, f, np.abs(Hm)))
            vals.append(float(20 * np.log10(am / (a1 + 1e-30) + 1e-30)))
        out[m] = vals
    return out
