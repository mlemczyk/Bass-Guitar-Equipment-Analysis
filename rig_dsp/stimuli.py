"""
Test signals ("probes") used for every re-amp measurement in this dataset.

This is the generator the original captures were made with
(`Equipment_model/probes.py` in the source project), with the project paths
removed. `stimuli/generate.py` writes the WAVs, which should match
`stimuli/*.wav` exactly; `stimuli/README.md` records the check.

Every probe is played from the computer at a peak level set at re-amp time
(`send_peak_dbfs` in each measurement's `capture` block). That rescales the
whole file, so the level structure inside a probe (the ladder's 10dB steps, for
example) is kept.
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 44100
PROBE_PEAK_DBFS = -12.0          # peak level the files are written at
SWEEP_SECONDS = 20.0
F_START, F_END = 15.0, 20000.0

ESS_LADDER_LEVELS = (-60.0, -50.0, -40.0, -30.0, -20.0)   # file levels, dBFS peak
ESS_LADDER_SECONDS = 8.0
ESS_LADDER_GAP = 1.5
ESS_LADDER_LEAD = 1.0

LEVELS_HZ = 110.0
LEVELS_DB = (-40, -34, -28, -22, -16, -10, -6, -3)          # before the -12dB file scaling
LEVELS_STEP_SEC, LEVELS_GAP_SEC = 1.5, 0.5


def norm(y: np.ndarray, peak_dbfs: float = PROBE_PEAK_DBFS) -> np.ndarray:
    target = 10 ** (peak_dbfs / 20.0)
    return (y / (np.max(np.abs(y)) + 1e-12) * target).astype(np.float32)


def exponential_sweep(seconds=SWEEP_SECONDS, f0=F_START, f1=F_END, sr=SAMPLE_RATE):
    """Farina exponential sine sweep and its matched inverse filter.

    Convolving a recorded output with `inverse` collapses the sweep to an
    impulse response; harmonic order m lands `seconds * ln(m) / ln(f1/f0)`
    ahead of the linear impulse, so each order can be windowed out alone."""
    n = int(seconds * sr)
    t = np.arange(n) / sr
    k = np.log(f1 / f0)
    sweep = np.sin(2 * np.pi * f0 * seconds / k * (np.exp(t * k / seconds) - 1.0))
    fade = int(0.05 * sr)
    win = np.ones(n)
    win[:fade] = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade)))
    win[-fade:] = win[:fade][::-1]
    sweep *= win
    inverse = sweep[::-1] * np.exp(-t * k / seconds)
    return sweep, inverse


def pink_noise(seconds=20.0, sr=SAMPLE_RATE, seed=20260913):
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    spec = rng.normal(size=n // 2 + 1) + 1j * rng.normal(size=n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / sr)
    shape = np.ones_like(f)
    shape[1:] = 1.0 / np.sqrt(f[1:])
    shape[0] = 0.0
    return np.fft.irfft(spec * shape, n)


def level_steps(sr=SAMPLE_RATE, freq=LEVELS_HZ, step_sec=LEVELS_STEP_SEC,
                gap_sec=LEVELS_GAP_SEC, levels_db=LEVELS_DB):
    """Steady 110Hz (A1) tones rising in level, with silence between."""
    out = []
    gap = np.zeros(int(gap_sec * sr))
    for db in levels_db:
        t = np.arange(int(step_sec * sr)) / sr
        tone = np.sin(2 * np.pi * freq * t) * (10 ** (db / 20.0))
        fade = int(0.02 * sr)
        tone[:fade] *= np.linspace(0, 1, fade)
        tone[-fade:] *= np.linspace(1, 0, fade)
        out.append(gap)
        out.append(tone)
    out.append(gap)
    return np.concatenate(out)


def ess_ladder(sr=SAMPLE_RATE):
    """The same exponential sweep at five levels 10dB apart, so linearity is
    measured rather than assumed."""
    sweep, _ = exponential_sweep(seconds=ESS_LADDER_SECONDS, sr=sr)
    parts = [np.zeros(int(ESS_LADDER_LEAD * sr))]
    for db in ESS_LADDER_LEVELS:
        parts.append(sweep / (np.max(np.abs(sweep)) + 1e-12) * 10 ** (db / 20.0))
        parts.append(np.zeros(int(ESS_LADDER_GAP * sr)))
    return np.concatenate(parts).astype(np.float32)


TWOTONE_LOW_HZ = 80.0
TWOTONE_PROBE_HZ = (437.0, 1249.0, 3527.0)
TWOTONE_PROBE_DBFS = -38.0
TWOTONE_LOW_STEPS = (-55, -45, -35, -25, -15)
TWOTONE_STEP_SEC, TWOTONE_GAP_SEC = 2.5, 1.0


def two_tone(sr=SAMPLE_RATE):
    """Three quiet probe tones held constant while a loud 80Hz tone steps up
    underneath: tells a multiband compressor from a broadband one."""
    probes = sum(np.sin(2 * np.pi * f * np.arange(int(
        (len(TWOTONE_LOW_STEPS) * (TWOTONE_STEP_SEC + TWOTONE_GAP_SEC) + 2.0) * sr)) / sr)
        for f in TWOTONE_PROBE_HZ) / len(TWOTONE_PROBE_HZ)
    probes *= 10 ** (TWOTONE_PROBE_DBFS / 20.0)
    low = np.zeros_like(probes)
    pos = int(1.0 * sr)
    fade = int(0.01 * sr)
    for db in TWOTONE_LOW_STEPS:
        n = int(TWOTONE_STEP_SEC * sr)
        t = np.arange(n) / sr
        seg = np.sin(2 * np.pi * TWOTONE_LOW_HZ * t) * 10 ** (db / 20.0)
        seg[:fade] *= np.linspace(0, 1, fade)
        seg[-fade:] *= np.linspace(1, 0, fade)
        low[pos:pos + n] += seg
        pos += n + int(TWOTONE_GAP_SEC * sr)
    return (probes + low).astype(np.float32)


BURST_HZ = 110.0
BURST_LOUD_DBFS, BURST_QUIET_DBFS = -14.0, -44.0
BURST_LOUD_SEC, BURST_QUIET_SEC = 1.5, 3.5
BURST_CYCLES = 5


def bursts(sr=SAMPLE_RATE):
    """110Hz alternating 30dB loud/quiet: attack and release times."""
    fade = int(0.002 * sr)
    parts = [np.zeros(int(0.5 * sr))]
    for _ in range(BURST_CYCLES):
        for db, secs in ((BURST_LOUD_DBFS, BURST_LOUD_SEC),
                         (BURST_QUIET_DBFS, BURST_QUIET_SEC)):
            n = int(secs * sr)
            t = np.arange(n) / sr
            seg = np.sin(2 * np.pi * BURST_HZ * t) * 10 ** (db / 20.0)
            seg[:fade] *= np.linspace(0, 1, fade)
            seg[-fade:] *= np.linspace(1, 0, fade)
            parts.append(seg)
    parts.append(np.zeros(int(1.0 * sr)))
    return np.concatenate(parts).astype(np.float32)


PLUCK_HZ = 55.0
PLUCK_LEVELS = (-34.0, -24.0, -14.0)
PLUCK_DECAY_SEC = 0.45
PLUCK_NOTE_SEC = 2.0
PLUCK_PER_LEVEL = 3
PLUCK_HARMONICS = 6


def _pluck_parts(sr, f0, seconds, decay):
    t = np.arange(int(seconds * sr)) / sr
    return [(np.sin(2 * np.pi * f0 * h * t) / h)
            * np.exp(-t / (decay / (1 + 0.6 * (h - 1))))
            for h in range(1, PLUCK_HARMONICS + 1)]


def _pluck(sr, f0, seconds, decay):
    y = np.sum(_pluck_parts(sr, f0, seconds, decay), axis=0)
    return y / (np.max(np.abs(y)) + 1e-12)


def _sustained_match(sr, f0, seconds, decay, scale):
    """Steady tone with the pluck's time-averaged spectrum, harmonic by
    harmonic, so only the envelope differs between the two."""
    parts = _pluck_parts(sr, f0, seconds, decay)
    t = np.arange(int(seconds * sr)) / sr
    out = np.zeros_like(t)
    for h, part in enumerate(parts, start=1):
        rms = float(np.sqrt(np.mean((part * scale) ** 2)))
        out += np.sin(2 * np.pi * f0 * h * t) * rms * np.sqrt(2)
    return out


def plucks(sr=SAMPLE_RATE):
    """Synthetic plucked notes against per-harmonic RMS-matched steady tones:
    is a compressor program-dependent?"""
    fade = int(0.01 * sr)
    parts = [np.zeros(int(0.5 * sr))]
    for db in PLUCK_LEVELS:
        target = 10 ** (db / 20.0)
        raw = _pluck(sr, PLUCK_HZ, PLUCK_NOTE_SEC, PLUCK_DECAY_SEC)
        scale = target / (np.max(np.abs(np.sum(
            _pluck_parts(sr, PLUCK_HZ, PLUCK_NOTE_SEC, PLUCK_DECAY_SEC), axis=0))) + 1e-12)
        for _ in range(PLUCK_PER_LEVEL):
            parts.append(raw * target)
            parts.append(np.zeros(int(0.4 * sr)))
        tone = _sustained_match(sr, PLUCK_HZ, PLUCK_NOTE_SEC, PLUCK_DECAY_SEC, scale)
        tone[:fade] *= np.linspace(0, 1, fade)
        tone[-fade:] *= np.linspace(1, 0, fade)
        for _ in range(PLUCK_PER_LEVEL):
            parts.append(tone)
            parts.append(np.zeros(int(0.4 * sr)))
    parts.append(np.zeros(int(1.0 * sr)))
    return np.concatenate(parts).astype(np.float32)


def all_probes(sr=SAMPLE_RATE):
    """(filename, samples, description) for every probe, as written to disk."""
    sweep, inverse = exponential_sweep(sr=sr)
    return [
        ("ess.wav", norm(sweep), "20s exponential sine sweep, 15Hz-20kHz"),
        ("ess_inverse.wav", norm(inverse), "matched inverse filter for ess.wav (never re-amped)"),
        ("pink.wav", norm(pink_noise(sr=sr)), "20s pink noise, seed 20260913"),
        ("levels.wav", (level_steps(sr=sr) * 10 ** (PROBE_PEAK_DBFS / 20.0)).astype(np.float32),
         "8 steps of 110Hz, -40 to -3dB relative, 1.5s each with 0.5s gaps"),
        ("silence.wav", np.zeros(int(10 * sr), dtype=np.float32), "10s digital silence"),
        ("ess_ladder.wav", ess_ladder(sr=sr),
         "8s sweep at -60/-50/-40/-30/-20dBFS, 1.5s gaps, 1s lead"),
        ("twotone.wav", two_tone(sr=sr), "3 quiet tones over a stepping 80Hz tone"),
        ("bursts.wav", bursts(sr=sr), "5 loud/quiet 110Hz cycles"),
        ("plucks.wav", plucks(sr=sr), "synthetic plucks vs RMS-matched steady tones"),
    ]
