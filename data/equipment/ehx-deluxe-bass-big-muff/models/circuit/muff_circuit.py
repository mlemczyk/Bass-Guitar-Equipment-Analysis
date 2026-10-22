#!/usr/bin/env python3
"""
muff_circuit.py

The Big Muff's fuzz core as a CIRCUIT, not a fitted black box.

    python muff_circuit.py selftest       # DC operating point, speed, a sine

WHY (user, 2026-10-18). `muff_model.py` is a Wiener-Hammerstein fit: one
pre-filter, one memoryless shaper, one post-filter. It holds near the settled
setting (2.2dB on music) and not away from it (`muff_generalise.py`), because a
black box has no idea what Sustain or Tone physically are. A circuit model
does: Sustain is a pot dividing the signal between two transistor stages, Tone
is a pot across a passive network, and the diodes clip through a coupling cap,
so the clipping is frequency-dependent in exactly the way a single shaper
cannot be.

WHICH CIRCUIT. No schematic of the Deluxe Bass Big Muff is public (searched
2026-10-18: the Big Muff Page refuses current EHX models, the freestompboxes
trace is the plain Bass Big Muff). EHX says the Deluxe Bass is based on the
'90s Black Russian Big Muff, and the plain Bass Big Muff's trace shows Russian
values too, so the core here is the Black Russian, from General Guitar
Gadgets' build sheet (`ggg_bmp_rusb_sc.pdf` / `_bom.pdf`, 2012):

    Q1 input booster   R1 39k  C1 100n  R2 100k  R3 470k||C2 470p  R5 12k  R4 390
    Sustain            C3 100n -> R6 100k log (bottom leg R7 1k) -> C4 100n
    Q2 clipper         R8 10k  R9 100k  R10 470k||C5 470p  D1/D2 + C6 47n  R11 12k  R12 390
    Q3 clipper         C7 100n R13 10k  R14 100k  R15 470k||C8 470p  D3/D4 + C9 47n  R17 12k  R16 390
    Tone stack         C10 3n9 / R18 22k (treble leg)  R19 22k / C11 10n (bass leg)  R20 100k lin
    Q4 output          C12 100n  R22 470k / R21 100k  R24 10k  R23 2k7  C13 100n -> Volume 100k
    Q1-Q4 2N5088, D1-D4 1N914

The bass versions are reported (informally) to change capacitor values, so
`muff_circuit_fit.py` lets five capacitor GROUPS scale from these values and
fits the scale. That is the grey-box half: the topology is fixed, the parts
are priors.

WHAT IS NOT IN IT. The Deluxe's input buffer, Blend, output stage, gate and
crossover. The buffer and output stage are taken as flat gains (fitted), Blend
as a crossfade against the flat dry path (see model.py), the
crossover as out (it is not modelled) and the gate as open (it
sits at 9:00; fits exclude decays).

THE SOLVER. Nodal analysis discretised with the trapezoidal rule and reduced
by the DK method (Yeh 2009; Holters & Zolzer 2011): the linear part becomes a
13-state update, and only the 10 nonlinear port voltages (two Ebers-Moll
junctions per transistor, one antiparallel pair per clipper) are solved by
Newton each sample. Run at 2x oversampling.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

import numpy as np
from numba import njit

VT = 0.02585

# 2N5088 (Fairchild SPICE model) and 1N914.
BJT = dict(Is=5.911e-15, bf=1122.0, br=1.271)
DIODE = dict(Is=2.52e-9, n=1.752)

# Black Russian values. Keys are the GGG designators.
PARTS = dict(
    R1=39e3, R2=100e3, R3=470e3, R4=390.0, R5=12e3, R7=1e3, R8=10e3, R9=100e3,
    R10=470e3, R11=12e3, R12=390.0, R13=10e3, R14=100e3, R15=470e3, R16=390.0,
    R17=12e3, R18=22e3, R19=22e3, R21=100e3, R22=470e3, R23=2.7e3, R24=10e3,
    C1=100e-9, C2=470e-12, C3=100e-9, C4=100e-9, C5=470e-12, C6=47e-9,
    C7=100e-9, C8=470e-12, C9=47e-9, C10=3.9e-9, C11=10e-9, C12=100e-9,
    C13=100e-9,
    POT=100e3, RLOAD=100e3, VCC=9.0,
)

# Capacitor groups the fit may scale. "Bass versions double the caps" is a
# forum claim, so it is a hypothesis the fit can confirm or reject per group.
CAP_GROUPS = {
    "coupling": ("C1", "C3", "C4", "C7", "C12", "C13"),
    "miller": ("C2", "C5", "C8"),
    "clip": ("C6", "C9"),
    "tone_treble": ("C10",),
    "tone_bass": ("C11",),
}


def clock_to_travel(pos) -> float:
    """Knob clock position (or 'min'/'max') to rotation 0..1, 7:00 -> 5:00."""
    if isinstance(pos, (int, float)):
        return float(pos)
    s = str(pos).strip().lower()
    if s.startswith("min"):
        return 0.0
    if s.startswith("max"):
        return 1.0
    h, m = s.split(":")
    hours = (int(h) % 12) + int(m) / 60.0      # 7:00 -> 7, 5:00 -> 5
    return float(np.clip(((hours - 7.0) % 12.0) / 10.0, 0.0, 1.0))


def log_taper(t: float, a_mid: float) -> float:
    """Fraction of an audio-taper pot below the wiper at rotation t.
    `a_mid` is the fraction at half rotation (10-20% for real A-taper pots)."""
    b = ((1.0 - a_mid) / a_mid) ** 2
    return float((b ** t - 1.0) / (b - 1.0))


@dataclass
class Settings:
    sustain: float = 0.5          # rotation 0..1
    tone: float = 1.0             # rotation 0..1, 1 = full clockwise = treble
    sustain_mid: float = 0.15     # taper of the Sustain pot
    cap_scale: dict = field(default_factory=dict)
    bjt: dict = field(default_factory=lambda: dict(BJT))
    diode: dict = field(default_factory=lambda: dict(DIODE))


# --------------------------------------------------------------------------
# Netlist -> DK matrices
# --------------------------------------------------------------------------

def netlist(s: Settings):
    p = dict(PARTS)
    for g, names in CAP_GROUPS.items():
        for n in names:
            p[n] = p[n] * float(s.cap_scale.get(g, 1.0))
    a = log_taper(s.sustain, s.sustain_mid)
    rmin = 1.0
    R = [
        ("vin", "n1", p["R1"]), ("b1", "0", p["R2"]), ("c1", "b1", p["R3"]),
        ("e1", "0", p["R4"]), ("vcc", "c1", p["R5"]),
        ("stop", "sw", max((1 - a) * p["POT"], rmin)),
        ("sw", "sbot", max(a * p["POT"], rmin)), ("sbot", "0", p["R7"]),
        ("n2", "b2", p["R8"]), ("b2", "0", p["R9"]), ("c2", "b2", p["R10"]),
        ("vcc", "c2", p["R11"]), ("e2", "0", p["R12"]),
        ("n3", "b3", p["R13"]), ("b3", "0", p["R14"]), ("c3", "b3", p["R15"]),
        ("vcc", "c3", p["R17"]), ("e3", "0", p["R16"]),
        ("tA", "0", p["R18"]), ("c3", "tB", p["R19"]),
        ("tA", "tw", max((1 - s.tone) * p["POT"], rmin)),
        ("tw", "tB", max(s.tone * p["POT"], rmin)),
        ("vcc", "b4", p["R22"]), ("b4", "0", p["R21"]),
        ("vcc", "c4", p["R24"]), ("e4", "0", p["R23"]),
        ("out", "0", p["RLOAD"]),
    ]
    C = [
        ("n1", "b1", p["C1"]), ("c1", "b1", p["C2"]), ("c1", "stop", p["C3"]),
        ("sw", "n2", p["C4"]), ("c2", "b2", p["C5"]), ("d2", "c2", p["C6"]),
        ("c2", "n3", p["C7"]), ("c3", "b3", p["C8"]), ("d3", "c3", p["C9"]),
        ("c3", "tA", p["C10"]), ("tB", "0", p["C11"]), ("tw", "b4", p["C12"]),
        ("c4", "out", p["C13"]),
    ]
    # Nonlinear ports (positive node, negative node). Each BJT contributes
    # (b,e) then (b,c); each clipper one antiparallel pair.
    bjts = [("c1", "b1", "e1"), ("c2", "b2", "e2"), ("c3", "b3", "e3"), ("c4", "b4", "e4")]
    ports = []
    for c, b, e in bjts:
        ports += [(b, e), (b, c)]
    ports += [("b2", "d2"), ("b3", "d3")]
    vsrc = [("vin", "0"), ("vcc", "0")]
    return R, C, ports, vsrc, p


def dk_matrices(s: Settings, fs: float):
    R, C, ports, vsrc, p = netlist(s)
    names = sorted({n for el in R + C + ports + vsrc for n in el[:2]} - {"0"})
    idx = {n: i for i, n in enumerate(names)}
    nn = len(names)
    nv = len(vsrc)
    dim = nn + nv

    def inc(a, b):
        v = np.zeros(nn)
        if a != "0":
            v[idx[a]] += 1.0
        if b != "0":
            v[idx[b]] -= 1.0
        return v

    S = np.zeros((dim, dim))
    for a, b, r in R:
        v = inc(a, b)
        S[:nn, :nn] += np.outer(v, v) / r
    Gc = np.array([2.0 * c * fs for *_, c in C])
    Nc = np.array([inc(a, b) for a, b, _ in C])
    S[:nn, :nn] += Nc.T @ np.diag(Gc) @ Nc
    Nu = np.zeros((nv, dim))
    for k, (a, b) in enumerate(vsrc):
        v = inc(a, b)
        S[:nn, nn + k] = v
        S[nn + k, :nn] = v
        Nu[k, nn + k] = 1.0
    Nn = np.array([inc(a, b) for a, b in ports])
    Nc_ = np.hstack([Nc, np.zeros((len(C), nv))])
    Nn_ = np.hstack([Nn, np.zeros((len(ports), nv))])
    No = np.zeros(dim)
    No[idx["out"]] = 1.0

    Si = np.linalg.inv(S)
    # S z = Nc^T x + Nu^T u - Nn^T i   (port current flows + -> - inside the device)
    A = 2.0 * np.diag(Gc) @ Nc_ @ Si @ Nc_.T - np.eye(len(C))
    B = 2.0 * np.diag(Gc) @ Nc_ @ Si @ Nu.T
    Cm = -2.0 * np.diag(Gc) @ Nc_ @ Si @ Nn_.T
    D = Nn_ @ Si @ Nc_.T
    E = Nn_ @ Si @ Nu.T
    F = -Nn_ @ Si @ Nn_.T
    Do = No @ Si @ Nc_.T
    Eo = No @ Si @ Nu.T
    Fo = -No @ Si @ Nn_.T
    dev = np.array([s.bjt["Is"], s.bjt["bf"], s.bjt["br"],
                    s.diode["Is"], s.diode["n"] * VT])
    return dict(A=A, B=B, C=Cm, D=D, E=E, F=F, Do=Do, Eo=Eo, Fo=Fo, dev=dev,
                vcc=p["VCC"])


# --------------------------------------------------------------------------
# The per-sample solver
# --------------------------------------------------------------------------

EXP_CAP = 60.0


@njit(cache=True, fastmath=False)
def _lexp(z):
    """exp with a linear continuation above EXP_CAP, so Newton cannot overflow."""
    if z > EXP_CAP:
        return np.exp(EXP_CAP) * (1.0 + z - EXP_CAP), np.exp(EXP_CAP)
    e = np.exp(z)
    return e, e


@njit(cache=True)
def _devices(v, dev, i, J):
    """Port currents i(v) and the (block-diagonal) Jacobian di/dv."""
    Is, bf, br, Isd, nvt = dev[0], dev[1], dev[2], dev[3], dev[4]
    n = v.shape[0]
    for r in range(n):
        for c in range(n):
            J[r, c] = 0.0
    for q in range(4):
        k = 2 * q
        ebe, dbe = _lexp(v[k] / VT)
        ebc, dbc = _lexp(v[k + 1] / VT)
        ic = Is * (ebe - ebc) - Is / br * (ebc - 1.0)
        ib = Is / bf * (ebe - 1.0) + Is / br * (ebc - 1.0)
        dic_be = Is * dbe / VT
        dic_bc = -Is * dbc / VT - Is / br * dbc / VT
        dib_be = Is / bf * dbe / VT
        dib_bc = Is / br * dbc / VT
        i[k] = ib + ic
        i[k + 1] = -ic
        J[k, k] = dib_be + dic_be
        J[k, k + 1] = dib_bc + dic_bc
        J[k + 1, k] = -dic_be
        J[k + 1, k + 1] = -dic_bc
    for q in range(2):
        k = 8 + q
        ep, dp = _lexp(v[k] / nvt)
        em, dm = _lexp(-v[k] / nvt)
        i[k] = Isd * (ep - em)
        J[k, k] = Isd * (dp + dm) / nvt


@njit(cache=True)
def _solve_inplace(M, b, n):
    """Gaussian elimination with partial pivoting; the solution replaces b."""
    for k in range(n):
        piv = k
        best = abs(M[k, k])
        for r in range(k + 1, n):
            if abs(M[r, k]) > best:
                best = abs(M[r, k])
                piv = r
        if piv != k:
            for c in range(n):
                tmp = M[k, c]
                M[k, c] = M[piv, c]
                M[piv, c] = tmp
            tmp = b[k]
            b[k] = b[piv]
            b[piv] = tmp
        inv = 1.0 / M[k, k]
        for r in range(k + 1, n):
            f = M[r, k] * inv
            if f != 0.0:
                for c in range(k, n):
                    M[r, c] -= f * M[k, c]
                b[r] -= f * b[k]
    for k in range(n - 1, -1, -1):
        s = b[k]
        for c in range(k + 1, n):
            s -= M[k, c] * b[c]
        b[k] = s / M[k, k]


@njit(cache=True)
def _run(x_in, vcc, A, B, Cm, D, E, F, Do, Eo, Fo, dev, state, vguess):
    nx = A.shape[0]
    nn = D.shape[0]
    y = np.empty(x_in.shape[0])
    x = state.copy()
    v = vguess.copy()
    i = np.zeros(nn)
    J = np.zeros((nn, nn))
    p = np.zeros(nn)
    M = np.zeros((nn, nn))
    g = np.zeros(nn)
    fails = 0
    for t in range(x_in.shape[0]):
        u0 = x_in[t]
        for r in range(nn):
            acc = E[r, 0] * u0 + E[r, 1] * vcc
            for c in range(nx):
                acc += D[r, c] * x[c]
            p[r] = acc
        ok = False
        for it in range(60):
            _devices(v, dev, i, J)
            # g = v - p - F i ;  M = I - F J
            for r in range(nn):
                acc = v[r] - p[r]
                for c in range(nn):
                    acc -= F[r, c] * i[c]
                g[r] = acc
                for c in range(nn):
                    s = 0.0
                    for k in range(nn):
                        s += F[r, k] * J[k, c]
                    M[r, c] = (1.0 if r == c else 0.0) - s
            _solve_inplace(M, g, nn)
            big = 0.0
            for r in range(nn):
                d = g[r]
                if d > 0.2:
                    d = 0.2
                elif d < -0.2:
                    d = -0.2
                v[r] -= d
                if abs(d) > big:
                    big = abs(d)
            if big < 1e-10:
                ok = True
                break
        if not ok:
            fails += 1
        _devices(v, dev, i, J)
        acc = Eo[0] * u0 + Eo[1] * vcc
        for c in range(nx):
            acc += Do[c] * x[c]
        for c in range(nn):
            acc += Fo[c] * i[c]
        y[t] = acc
        xn = np.empty(nx)
        for r in range(nx):
            s = B[r, 0] * u0 + B[r, 1] * vcc
            for c in range(nx):
                s += A[r, c] * x[c]
            for c in range(nn):
                s += Cm[r, c] * i[c]
            xn[r] = s
        x = xn
    return y, x, v, fails


class MuffCore:
    """One Settings, one sample rate, a settled DC operating point."""

    def __init__(self, s: Settings, fs: float = 88200.0):
        self.fs = fs
        self.m = dk_matrices(s, fs)
        nx, nn = self.m["A"].shape[0], self.m["D"].shape[0]
        self.state = np.zeros(nx)
        self.v = np.zeros(nn)
        self.fails = 0
        self._settle()

    def _settle(self, seconds=1.5):
        """Bring the supply up and let every coupling cap charge."""
        m = self.m
        n = int(seconds * self.fs)
        ramp = np.minimum(np.arange(n) / (0.05 * self.fs), 1.0)
        # ramp the supply by running with vcc scaled: emulate by chunks
        for frac in np.linspace(0.1, 1.0, 10):
            _, self.state, self.v, _ = _run(np.zeros(int(0.01 * self.fs)), m["vcc"] * frac,
                                            m["A"], m["B"], m["C"], m["D"], m["E"], m["F"],
                                            m["Do"], m["Eo"], m["Fo"], m["dev"],
                                            self.state, self.v)
        _, self.state, self.v, _ = _run(np.zeros(n), m["vcc"], m["A"], m["B"], m["C"],
                                        m["D"], m["E"], m["F"], m["Do"], m["Eo"], m["Fo"],
                                        m["dev"], self.state, self.v)
        del ramp
        y0, _, _, _ = _run(np.zeros(16), m["vcc"], m["A"], m["B"], m["C"], m["D"], m["E"],
                           m["F"], m["Do"], m["Eo"], m["Fo"], m["dev"], self.state, self.v)
        self.dc_out = float(y0[-1])

    def process(self, volts: np.ndarray) -> np.ndarray:
        m = self.m
        y, self.state, self.v, f = _run(np.ascontiguousarray(volts, dtype=np.float64),
                                        m["vcc"], m["A"], m["B"], m["C"], m["D"], m["E"],
                                        m["F"], m["Do"], m["Eo"], m["Fo"], m["dev"],
                                        self.state, self.v)
        self.fails += int(f)
        return y - self.dc_out


def simulate(x, sr, s: Settings, k_in: float, oversample: int = 2) -> np.ndarray:
    """Digital audio in (pedal-input scale), core output volts out, at `sr`.

    `k_in` is volts at the core's input per unit of digital full scale -- the
    re-amp loop and the Deluxe's input buffer, lumped. The caller applies the
    output gain."""
    from scipy import signal
    x = np.asarray(x, dtype=np.float64)
    xu = signal.resample_poly(x, oversample, 1) if oversample > 1 else x
    core = MuffCore(s, fs=sr * oversample)
    y = core.process(xu * k_in)
    if oversample > 1:
        y = signal.resample_poly(y, 1, oversample)
    return y[:len(x)]


def _selftest():
    s = Settings()
    t0 = time.time()
    core = MuffCore(s, 88200.0)
    print(f"  settle + JIT: {time.time() - t0:.1f}s, output DC {core.dc_out:+.3f} V")
    # operating point: port voltages
    print("  Vbe/Vbc per transistor:",
          " ".join(f"Q{q+1} {core.v[2*q]:.3f}/{core.v[2*q+1]:.3f}" for q in range(4)))
    sr = 44100
    tt = np.arange(int(2.0 * sr)) / sr
    for amp in (0.001, 0.01, 0.1, 0.5):
        x = amp * np.sin(2 * np.pi * 110 * tt)
        t0 = time.time()
        y = simulate(x, sr, s, k_in=1.0)
        dt = time.time() - t0
        seg = y[sr // 2:]
        w = np.hanning(len(seg))
        spec = np.abs(np.fft.rfft(seg * w))
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        h = [np.sqrt(np.sum(spec[np.abs(f - k * 110) < 4] ** 2)) for k in range(1, 6)]
        rel = " ".join(f"{20*np.log10(hk/h[0]+1e-20):6.1f}" for hk in h[1:])
        print(f"  in {amp:6.3f} V  gain {20*np.log10(np.max(np.abs(seg))/amp):+6.1f} dB  "
              f"h2..h5 re h1 {rel}   {dt:.1f}s for 2s audio")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        _selftest()
    else:
        print(__doc__)
