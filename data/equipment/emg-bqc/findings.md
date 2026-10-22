# EMG BQC (HZ) onboard preamp — findings

The active preamp in a Yamaha TRBX305, driving the stock passive pickups: Bass,
Mid, MidFreq, Treble, pickup pan, and two internal treble DIP switches (left
OFF/OFF). It runs at 18V from two 9V LiPo batteries (16.06V in use). Measured
2026-09-13 by **magnetic injection**: a headphone transducer laid on the body
between the pickups, strings damped, driving a sweep into the coils. Every
curve is a take divided by the EMG-flat reference H00 from the same session, so
the transducer, its coupling, the pickup resonance and the flux tilt cancel.
Method: `../../../methodology.md`, section 8.

Controls are in **notches from centre, −5..+5**.

## Session validity

The closing reference H99 reproduces the opening H00 to **0.46dB standard
deviation** across 20Hz–15kHz. Worst drift by region: Bass and Mid regions
1.1dB (against 12–15dB effects), Treble region 1.7–1.9dB. One exception: a
transducer resonance at **2845Hz** grew from −2.0 to −5.5dB over the session.
**Don't quote any single figure between 2.8 and 3.6kHz** (±5dB).

## Headline numbers

| Control | Measured | The documentation said |
|---|---|---|
| Bass | low shelf, **half-gain corner 160–265Hz**, ±12.5dB at 50Hz, still ±2.6dB at 374Hz | "6dB/octave centred at 50Hz" |
| Treble (DIP OFF/OFF) | high shelf, **corner ~2.3kHz**, ±11.3 to ±12.1dB at 12kHz, only **+0.9dB at 400Hz** | "onset ~300Hz, peak effect ~2.5–3kHz" |
| Mid | **peaking, Q 0.93–1.31**, ±12.9 to ±15.3dB | ±12dB, no Q given |
| MidFreq | centre 112 / 196 / 374–390 / 696 / 1038–1077Hz at −5 / −2.5 / 0 / +2.5 / +5. Octaves per 2.5 notches: 0.81, 0.95, 0.87, **0.55** | 100Hz–1kHz |
| Taper, every control | **±2 notches ≈ ±2dB, ±5 ≈ ±12–15dB**. Symmetric | — |

### Bass (dB)

| position | 50Hz | 112 | 196 | 374 | 1k+ |
|---|---|---|---|---|---|
| −5 | −12.6 | −11.1 | −5.7 | −2.6 | ≈0 |
| −2 | −1.9 | −1.7 | −1.4 | −1.1 | ≈0 |
| +2 | +2.0 | +1.9 | +1.5 | +1.2 | ≈0 |
| +5 | +12.5 | +11.1 | +5.8 | +2.6 | ≈0 |

### Treble (dB)

| position | 400Hz | 1k | 2k | 3k* | 8k | 12k |
|---|---|---|---|---|---|---|
| −5 | −0.3 | −1.6 | −4.8 | −7.0 | −10.9 | −11.3 |
| −2 | −0.1 | −1.1 | −1.7 | −1.8 | −2.2 | −2.2 |
| +2 | +0.7 | +1.1 | +1.7 | +2.1 | +2.1 | +2.2 |
| +5 | +0.9 | +2.0 | +5.3 | +8.0 | +11.5 | +12.1 |

\* inside the transducer-resonance band, ±5dB.

### Mid

| MidFreq | centre (cut / boost) | Q (cut / boost) | depth at −5 / +5 |
|---|---|---|---|
| −5 | 113 / 112Hz | 1.27 / 1.31 | −12.9 / +13.9 |
| −2.5 | — / 196Hz | — / 1.04 | — / +14.1 |
| 0 | 374 / 390Hz | 1.11 / 0.93 | −15.3 / +14.9 |
| +2.5 | — / 696Hz | — / 1.14 | — / +15.1 |
| +5 | 1038 / 1077Hz | 1.16 / 1.05 | −12.9 / +13.2 |

Cut and boost centres agree within 4%. The MidFreq law is log-ish but not
log: log interpolation predicts 595Hz at +2.5, and the measurement is 696Hz.
Use the five points.

## Played validation

Played takes against the injected curves (long-term average spectra of
different performances, so the floor is ~0.8dB take to take):

| recipe | injected curve | prediction error |
|---|---|---|
| Mid −5 @ MidFreq 0 (a cut) | H13 | **2.08dB RMS**. The 400–1000Hz band matches to +0.27dB |
| Mid +2 @ MidFreq −5 | H11 | **0.96dB RMS** |
| Mid +5 @ MidFreq −5 (a +14dB boost) | H12 | **3.59dB RMS**: less low end and +3.6 to +6.3dB more 250Hz–2kHz than predicted. The take peaked at −8.9dBFS at the mixer |

The boosted case behaves like something clipping. The source project put it
down to the preamp running out of headroom. **Two later results argue
against that:**
1. Fresh 19.28V lithium primary cells (E04) in place of the 16.06V pack
   changed nothing (3.30 vs 3.59dB).
2. The signal path after the jack (the Tidal Wave's DI and mixer channel M2)
   is the re-amp loop's return path, and that path distorts by 0.7% at
   −17dBFS and 5.5% at −14dBFS on a steady tone (`interface/README.md`).
   A take peaking at −8.9dBFS is well into that region.

**So the Mid +5 nonlinearity is more likely the rig's return path than the
EMG.** That is not proven: the decisive check is a loud low note at Mid +5
captured on the Hi-Z M1 input, which bypasses the pedalboard and the Tidal
Wave DI.

## Pickup pan

Not measurable by injection (with the strings damped, pan is only an
electrical blend of two coils). Played takes at pan +5 / 0 / −5 show both
extremes **above** the centre in the 250–400Hz band (+6.1 / +6.3dB) and in
presence and brilliance. A blend of two sources can only do that if they cancel
at the centre: the two pickups' position combs summing to real nulls.
Absolute pan curves are not given, because the neck pickup is simply louder
and no anchor band exists. See `../instrument-trbx305/`.

## Not measured

- Treble DIP positions OFF/ON, ON/OFF, ON/ON. Changing them means opening the
  control cavity, which moves the bass and the transducer. They need their own
  session with their own reference pair.
- An undamped-string coupling diagnostic. Draping cloth over the earcup did
  not reduce the signal, which argues for magnetic rather than acoustic
  coupling.
