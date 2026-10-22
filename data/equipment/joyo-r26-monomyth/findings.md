# Joyo R-26 Monomyth — findings

Bass overdrive (a Darkglass Alpha·Omega-style design): Drive, Voice, Blend,
Level, a switchable drive stage, two pre-drive switches labelled **Hi Boost**
and **Gain Boost** (called Bite and Growl in the source project's earlier
notes), and a six-band EQ (Bass shelf, 250Hz, 500Hz, 1.5kHz, 3kHz, Treble
shelf). Measured 2026-09-17 to 09-20 (MYTH01–MYTH42), every other pedal
bypassed. Settled (MYTH12): Drive 12:00, Voice 12:00, Blend 9:00, Level
11:00, EQ flat, both switches off.

Small-signal figures are from ladder rung 0 (sent at −63dBFS peak), Farina
route. EQ figures are relative to MYTH02 (engaged, drive stage off, EQ flat).

## Topology, measured end to end

```
                +--------------- DRIVE STAGE (switchable) ---------------+
  in --> Blend -|--> Hi Boost / Gain Boost --> Clip --> Voice -----------|--> EQ (6 band) --> Level --> out
         (dry) -|--------------------------------------------------------|
                +--------------------------------------------------------+
```

- **Both switches sit before the clipper.** Their effect is large small-signal
  and gone at high level (4.3 and 4.9dB of level-dependence), and they are
  **exactly inert with the drive stage off**: MYTH41 and MYTH42 match MYTH02
  and each other to 0.01dB.
- **Voice sits after the clipper.** Its filter is invariant across 38dB of
  clipper gain, and the Voice min/max drive curves are the same curve with a
  constant offset.
- **The EQ is outside the drive stage.** It works normally with the drive off.

## Headline numbers

| Property | Value | Evidence |
|---|---|---|
| Drive stage OFF, EQ flat, vs bypass | **−0.8dB**, −1.7dB at 31Hz, linear (spread 0.10dB). Harmonics −66dB | MYTH02 |
| Blend min (drive on) | a clean path: −1.7dB at 31Hz to −0.9dB at 4kHz, harmonics −73dB | MYTH13 |
| Blend crossfade | linear to **0.07dB RMS**. Wet fraction at 9:00 = **0.12** (ladder fit, −23dBFS send), ~0.32 at 12:00 | MYTH13/12/15 |
| Drive | a gain into a hard clipper: 12dB more output small-signal from min to 12:00, identical at high level. The pre-clip path is highpassed, so Drive does 3x less at 31Hz than at 500Hz | MYTH19–22 |
| Clipping character vs Drive | min: odd, total −58dB. 10:00: **H2 leads (+6.3dB even−odd)**, total −27. 12:00: H3 leads, −21. 2:00 and max: total flat (−20, −19), but H7–H9 climb up to 26dB. **Below 12:00 Drive sets how much; above, how hard** | MYTH19–22 |
| Odd/even balance | mildly odd-dominated, even−odd ≈ −4 to −5dB at Blend max (the Big Muff: −47dB) | MYTH15 |
| Voice | a linear mid control, not a clipper morph: min = −5.6dB at 500Hz (scoop), max = +4.6dB at 500Hz, spread 0.05dB. Even/odd moves only 2.9dB over the whole knob | MYTH16, MYTH18 |
| Hi Boost (small-signal, through the clipper) | +6.2dB at 125Hz falling to +1.8dB at 4kHz at Drive 12:00. Its effect on the harmonics is the same at Drive 12:00 and max (+0.3dB total, −3.2dB even−odd) | MYTH27, MYTH30 |
| Gain Boost | a **smile**: +8.3dB at 31Hz, +1.1dB at 500Hz, **+10.5dB at 4kHz** (Drive min). At Drive max only the part below ~125Hz survives | MYTH28, MYTH31, MYTH40 |
| Both switches at Drive max | add exactly at 31Hz (+0.02dB error), nothing above 500Hz, −2.2dB short of the sum at 125Hz | MYTH32 |

### The six-band EQ (drive off, small-signal, vs MYTH02)

| slider | ±5 at centre | shape |
|---|---|---|
| Bass shelf | **+18.6 / −17.5** at 31Hz | first-order, skirt to 1kHz (+3.4 at 500Hz) |
| 250Hz | +11.8 / −11.7 | peaking, centre on nominal, Q ≈ 1.6 |
| 500Hz | +10.3 / −10.2 | peaking, Q ≈ 1.4 |
| 1.5kHz | +11.3 / −11.2 | peaking, Q ≈ 1.2 |
| 3kHz | +11.2 / −11.1 | peaking, Q ≈ 0.85; at 2kHz nearly the same as the 1.5kHz slider |
| Treble shelf | **+17.9 / −17.4** at 8kHz | rises from ~250Hz |

- **Boost and cut are symmetric small-signal** (within 0.2–1.2dB).
- Every cut is linear across the whole ladder.
- **Two cuts superpose to 0.68dB RMS** (MYTH11: 250Hz + 1.5kHz at −5). The
  error is confined to the valley between them, where the real filter cuts
  less. **Four adjacent −5 cuts do not**: they under-add by 3–4dB in the
  400Hz–1kHz region (source project MEQ02, a re-amp of a played take).

## Read with care: "boosts are capped at +4 to +6dB"

The source project concluded that **every EQ boost delivers only +4 to +6dB at
playing level**, against 96–99% for cuts. Its evidence was the top ladder
rung. The boosted takes return at **−5.5 to −9.8dBFS** on that rung, and the
cuts at about −15dBFS. The re-amp loop itself distorts above about −21dBFS
return and is at 5.5% THD by −14 (`interface/README.md`). A cut lowers the
return level, so it escapes; a boost raises it, so it hits the loop. The
source project's control (7dB less input moved the boosted capture's peak
only 2.5dB) does not separate the pedal from the loop, because the loop's
return path is also upstream of the capture.

And the source project's own later test points the same way. On real
material through the whole pedal with the drive on, the EQ acted at its
**small-signal** response (quiet-rung curves predicted the measured EQ effect
to 2.1dB RMS; loud-rung curves were off by 12.7dB). **Treat the small-signal
curves as the EQ, and the boost cap as the rig's return path, not this pedal.**
The return path (NR300 return, Tidal Wave DI, mixer channel) is also the live
signal path, so on this rig a large boost does run out of headroom, just not
inside the Monomyth.

## Model (`models/asymmetric_clipper/`), parameters preserved, not re-run here

`out = (1−b)·dry + b·H2·f(H1·x)`: H1 is a first-order highpass (288Hz) times
a lowpass (1.85kHz). f is a soft clipper with different positive and negative
ceilings and a linear leak. H2 is the quiet-rung response of MYTH15 over
MYTH13. b = 0.225 at playing level. Fitted 2026-09-20 on the 110Hz level
steps and the ladder level-dependence: 2.45dB RMS on probe harmonics.
Validated on played-performance re-amps by the source project, as RMS error
over six spectral bands plus a THD descriptor: **2.20dB** settled (in-sample),
2.18dB Drive max / Voice min, **2.38dB at Blend max** (output moved 14dB).
The fitted parameters existed only in a temporary file in the source project.
They are preserved here, but the model has not been re-implemented and
re-validated in this repository. See that folder's README.

## Superseded

- "Voice morphs between two clipping circuits" / "Voice tracks THD, not
  brightness": Voice is a ~500Hz mid EQ after the clipper. Its THD effect is
  arithmetic, because boosting 250–500Hz lifts a 110Hz note's harmonics more
  than its fundamental.
- "Blend's taper is front-loaded": a mix fraction was read off a dB change in
  harmonics that the dry path doesn't carry. Fitted, it is 0 → 0.12 → 0.32 →
  1.0 across min / 9:00 / 12:00 / max.
- "Hi Boost is a ~2.8kHz high-mid boost" (the Darkglass documentation for
  Bite). Seen through the clipper it is a low-mid lift. With the drive stage
  off it is inert, so its raw filter shape was never isolated.
- `MYTH02_ess_ladder_lad30` was recorded after the board had moved to the Bass
  shelf at +5. It is kept in the source project as
  `INVALID_mislabelled_was_MYTH03_state_lad30.wav` and excluded here.
