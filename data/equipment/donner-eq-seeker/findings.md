# Donner EQ Seeker — findings

Ten-band graphic EQ (31.25Hz–16kHz, octave spacing) plus a Level slider.
Measured 2026-09-15 to 2026-10-18 by re-amping through the loop described in
`../../../methodology.md`. Sliders are counted in **notches, −5..+5**, with 0 at
the centre detent. Every number here comes from the per-take files in
`measurements/` and can be recomputed with `tools/export_eq_seeker.py`. Take
IDs (`SEEKnn`) are the citations.

Two analysis routes appear below (see `methodology.md#two-routes`):
**Farina** = deconvolved, 1/12-octave, the route the model is fitted to;
**legacy** = Welch PSD, third-octave means, the route the source project
published its numbers from. Legacy third-octave averaging reads a narrow peak
lower, so Farina peaks run ~0.5dB higher.

## Headline numbers

| Property | Value | Takes |
|---|---|---|
| Band centres | all ten on nominal (within the 1/12-octave grid) | SEEK03–12 |
| Full boost at +5, at the band's nominal centre | **+13.1 to +15.7dB** (Farina); +13.0 to +15.1 (legacy) | SEEK03–12 |
| Full cut at −5 | −12.9 (125Hz), −13.9 (1kHz) | SEEK13, SEEK14 |
| Boost/cut symmetry | symmetric to ~0.3dB at ±5 and ±2 | SEEK05/13, SEEK08/14, SEEK21/22 |
| Slider law | **strongly nonlinear**: ±2 gives ~±1.3dB, −3 ~−4dB, −4 ~−13dB, −5 ~−15dB | SEEK21, 22, 15, 24, 25, 27, 28, 29, 16 |
| Linearity, small signal | the five ladder rungs agree within **0.05dB** while the return stays below about −17dBFS peak | all ladder takes |
| Insertion (engaged flat vs bypassed) | **−1.0dB** across 125Hz–1kHz; −0.1 at 31Hz, −0.8 at 62Hz, −1.2 at 10kHz, −1.5 at 16kHz | SEEK02 vs SEEK01 |
| Added noise, engaged flat | **none measurable** (−100.3 vs −99.5dBFS bypassed; the 1dB insertion loss also attenuates upstream noise) | SEEK02, SEEK01 |
| Level slider | −5 = **−15.5dB**, flat across the band; +2 ≈ +6.0, +3 ≈ +7.0, +4 ≈ +9.0 (approximate) | SEEK19; source project BK04/05, PL03/04 |
| Harmonic distortion, small signal | h2 and h3 at a **median of −61dB** relative to the fundamental (rungs 0–2, every take). The worst values (−41 to −47dB) are all on the quietest rung, where the harmonic windows hold mostly noise | all ladder takes |

### Band table at +5 (one slider, others at 0), small-signal

| band | Farina at nominal centre | legacy, small-signal | legacy, top rung | take |
|---|---|---|---|---|
| 31.25Hz | +15.4 | +14.80 | +11.78 | SEEK03 |
| 62.5Hz | +14.4 | +13.97 | +11.18 | SEEK04 |
| 125Hz | +13.1 | +13.02 | +10.71 | SEEK05 |
| 250Hz | +15.7 | +15.11 | +11.76 | SEEK06 |
| 500Hz | +14.0 | +13.63 | +11.00 | SEEK07 |
| 1kHz | +14.1 | +13.60 | +10.86 | SEEK08 |
| 2kHz | +14.4 | +14.11 | +11.10 | SEEK09 |
| 4kHz | +14.1 | +13.70 | +11.02 | SEEK10 |
| 8kHz | +13.4 | +13.09 | +10.65 | SEEK11 |
| 16kHz | +14.2 | +14.00 | +11.56 | SEEK12 |

The "top rung" column is the loudest ladder sweep. Its ~2.8dB shortfall is
**not** the pedal; see "The boost compression is the loop" below.

Each band spans roughly one to one and a half octaves at −3dB from its peak,
so neighbours overlap heavily. The legacy route put the half-gain Q at 0.67–1.04.

### Slider law, measured

Gain at the deepest point of the cut or boost, small-signal (Farina):

| setting | 125/250Hz | 500/1k/2k | single 500Hz |
|---|---|---|---|
| +5 | | | +14.0 (SEEK07) |
| +2 | | | +1.4 (SEEK22) |
| −2 | −1.6 (SEEK27) | −2.5 (SEEK15) | −1.3 (SEEK21) |
| −3 | −3.6 (SEEK28) | −4.6 (SEEK24) | |
| −4 | −13.5 (SEEK29) | −14.4 (SEEK25) | |
| −5 | −17.1 (SEEK16) | | |

**The last two notches do most of the work, and −3 → −4 is a cliff of about
9dB.** On this unit a cut from −3 to −4 is the difference between a gentle tilt
and an almost full-depth notch. Any controller or solver that interpolates
linearly between notches will be badly wrong at −4.

### Combinations

| take | setting | deepest/highest point |
|---|---|---|
| SEEK15 | 500/1k/2k at −2 | −2.5dB at 1kHz, broad scoop |
| SEEK24 | 500/1k/2k at −3 | −4.6dB at 1kHz |
| SEEK25 | 500/1k/2k at −4 | −14.4dB at 1kHz |
| SEEK27 | 125+250 at −2 | −1.6dB at 125Hz |
| SEEK28 | 125+250 at −3 | −3.6dB |
| SEEK29 | 125+250 at −4 | −13.5dB at 250Hz |
| SEEK16 | 125+250 at −5 | −17.1dB at 250Hz |
| SEEK17 | all ten at +2 | +5.2 to +6.3dB, broad hump peaking 2–4kHz |

SEEK17 is the odd one out: one slider at +2 gives +1.4dB, but ten at +2 give
+6. No model in `models/` predicts it to better than 2.5dB when it is left out
of the fit. Overlapping skirts explain some of the excess. Ten sliders set to
"+2" by eye on a law this steep could explain the rest, but that is untested.

## The boost compression is the loop, not the pedal

The source project attributed the top rung's ~2.8dB loss on every boost to the
Seeker's output stage running out of headroom. **The data says otherwise.** The
`levels` probe (eight steady 110Hz steps) was captured through the loop with
the Seeker flat (SEEK20), with 125Hz at +5 (SEEK23), and with **every pedal
bypassed** (`LOOP-LEVELS`, the source project's `MYTH01_levels_lad`, in
`interface/measurements/`). Distortion tracks the level *returning to the interface*, whatever the
Seeker is doing:

| return level, fundamental (dBFS peak) | all bypassed | Seeker flat | Seeker 125Hz +5 |
|---|---|---|---|
| ≈ −21 | 0.21% | 0.22% | — |
| ≈ −17 | 0.72% | 0.62% | 0.55% |
| ≈ −14 to −15 | 5.5% | 2.6% | — |
| ≈ −12.5 | — | — | 15.3% |

With 125Hz at +5, the return reaches −17dBFS from an input step 10dB quieter
than the flat take needs. Both distort the same amount once they get there.
So the limit is downstream
of the Seeker, in the loop's return path, and it sits about **−21dBFS return
peak for 0.2% THD**. That path includes the volume pedal, the NR300 return,
the bypassed Tidal Wave's DI and the mixer's M2 channel at gain +5. This data
cannot say which of them it is.

Consequences:

- The Seeker's boosts are linear up to at least −17dBFS return. No pedal-internal
  compression was observed.
- The model is fitted to ladder rungs 0–2 only (sent at −70/−60/−50dBFS).
- **The single-level Level +5 capture (SEEK18) is unusable**: it returned at
  −5.4dBFS peak and reads +6.6dB at 31Hz falling to +2.1 at 8kHz, which is
  distortion, not a tilt. Only Level −5 (SEEK19) is a clean measurement.
- The same limit applies to every pedal measured through this loop. See
  `../../../interface/README.md`.

## Noise

Noise is measured from the end of each capture, after the last sweep, so every
figure includes the noise of the whole loop (computer send, every bypassed
stage, mixer). Read the differences, not the absolute values. RMS,
20Hz–20kHz, dBFS at the capture:

| state | noise | change vs engaged flat |
|---|---|---|
| bypassed (SEEK01) | −99.5 | +0.8 |
| engaged, flat (SEEK02) | −100.3 | 0 |
| Level −5 (SEEK19) | −104.9 | −4.6 |
| 31.25Hz +5 | −99.4 | +0.9 |
| 62.5Hz +5 | −95.6 | +4.7 |
| 125Hz +5 | −97.4 | +2.9 |
| 250Hz +5 | −98.8 | +1.5 |
| 500Hz +5 | −98.8 | +1.5 |
| 1kHz +5 | −98.4 | +1.9 |
| 2kHz +5 | −97.1 | +3.2 |
| 4kHz +5 | −96.0 | +4.3 |
| 8kHz +5 | −93.6 | +6.7 |
| 16kHz +5 | −92.6 | +7.7 |
| all ten at +2 | −96.0 | +4.3 |
| cuts (SEEK13–16, 21, 24, 25, 27, 28) | −100.4 to −101.3 | −0.1 to −0.9 |

- **Engaged and flat, the pedal adds nothing.** This agrees with the source
  project's earlier noise pass (2026-08-31), which found the EQ Seeker added
  no measurable noise over a −92.9dBFS no-pedal baseline.
- **A −15.5dB Level cut only lowers the noise 4.6dB.** So most of the noise
  in these captures comes from downstream of the Seeker, and the pedal's
  own output noise is below about −105dBFS on this scale.
- **Boosts raise noise by amplifying the hiss coming in, most at the top.**
  +5 at 16kHz costs 7.7dB of broadband noise, and 62.5Hz +5 costs 4.7dB
  (mains-hum harmonics). Per-band noise spectra are in each take's `noise`
  block.

## Open questions

- **SEEK26** (500/1k/2k at −5) was never recorded.
- **Level slider above 0**: only full-chain loudness estimates exist. A
  ladder capture of Level +2 and +4 sent at −70 to −40dBFS would settle it.
- **Where in the return path the loop distorts.** A `levels` capture with the
  Tidal Wave's DI replaced by a passive DI would split it.
- **SEEK17's +6dB.** Re-recording ten sliders at +2, checking each slider's
  position, would separate slider-position error from circuit interaction.

## Superseded results, and why they are kept

- **1.29dB/notch.** The first pass measured each band with a single sweep at
  −23dBFS send (the `ess` captures, still in every take file, marked
  `superseded`). That put the boost in the loop's distortion region, and it
  produced a clean-looking curve for every band. **An overdriven stage still
  deconvolves into a smooth, plausible curve.** That is why every setting is
  now measured with the five-level ladder.
- **"Superposition fails by 0.9–3.8dB with no consistent sign."** That was
  measured against an *assumed* slider law (−2 = 9.2% of full travel, scaled
  linearly). With the law fitted, independent bands predict the combinations
  to 1.7dB RMS when left out. See `models/graphic_eq/validation.json`.
- **"The output stage compresses boosts above about −30dBFS."** Corrected
  above: the compression is in the loop.
