# Methodology

How every measurement in this dataset was taken and analysed, and the
mistakes that taught each rule. Read this before comparing these numbers
with your own, or before adding a measurement.

## 1. Re-amping: content cancels, so the result is the stage

Every stage after the bass's output jack is measured by playing a recorded
signal (a probe) out of the computer, through the stage, and back in
(`interface/README.md` has the path). The source signal is byte-identical on
every pass, so a ratio of two captures cancels the content exactly, leaving
only the stage. A parameter sweep costs a knob turn and a replay.

**Every response is a ratio against a reference capture from the same
session**, normally the pedal engaged with every control at its neutral
setting, or bypassed. The reference's take ID is in each file's `reference`
block. Never divide by a reference from another session: the loop has moved
by up to 8dB between sessions (`interface/README.md#session-drift`).

Same-session reproducibility is 0.01dB. Played (non-re-amped) takes are
limited to about 0.81dB take to take.

## 2. Measure linearity; never assume it

**Standing protocol: every setting is captured with `ess_ladder`**: one 8s
exponential sweep (15Hz–20kHz) repeated at five levels 10dB apart, with
1.5s gaps (`stimuli/`). One capture gives a frequency response at five
levels, so whether the stage is linear is a *result*. Where the five
curves agree, any of them is the transfer function. Where they part, the
quietest is the small-signal response and the spread is the range where a
fixed filter is the wrong model.

Why: the EQ Seeker was first measured with single sweeps at one level, three
times, and the answers disagreed by 6–8dB. Every curve looked clean. **An
overdriven stage still deconvolves into a smooth, plausible curve**, and
nothing in a single-level measurement can flag it.

The send level is set per pedal (`send_peak_dbfs` on each rung): −30dBFS peak
for linear stages, so the rungs leave the computer at −70/−60/−50/−40/−30,
and −23 for drive stages, whose operating point is the point. The source
project's calibration put a −23dBFS-peak probe at about the level the bass
itself delivers to the pedalboard.

**Check `return_peak_dbfs` before trusting a top rung.** The loop itself
distorts above about −21dBFS return (`interface/README.md`). A pedal that
boosts pushes its own top rung into that region.

## 3. Mask what the noise floor can't resolve

A stage with gain lifts its own noise as well as the signal, so the quiet end
of a ladder can sink under it, and the deconvolution still returns a smooth
curve computed from hiss. The noise floor is measured from the end of the same
capture, after the last sweep. Bins within 10dB of either capture's floor are
dropped (`null` in the JSON).

## 4. Two routes, both kept {#two-routes}

- **Legacy (Welch).** Welch PSD (nperseg 16384) of each sweep segment, take
  divided by reference, averaged into third-octave bands. No phase. Every
  number the source project published came from this route, and the
  `legacy_*` fields reproduce them exactly. Third-octave averaging
  under-reads a narrow peak by ~0.5dB.
- **Farina.** Deconvolve the capture with the sweep's matched inverse filter,
  window the linear impulse response (−50ms to +600ms around its peak,
  half-Hann edges), and window each harmonic order m at its known offset
  `T·ln(m)/ln(f1/f0)` ahead of it. That gives a complex transfer function
  (magnitude **and** phase), smoothed to 1/12 octave, and each harmonic
  order's level against the fundamental. Each order is time-aligned to its
  own impulse, so phase excludes the loop's bulk latency. **Models are fitted
  to this route.**

## 5. Separate what the knob does from what the circuit around it does

- **Measure a blend-equipped pedal fully wet, then model the blend.** With a
  dry path mixed in, any control that changes the wet level changes how much
  of every other wet control survives, so every control appears to interact
  with every other. On the Big Muff, Tone × Sustain measured 9.28dB RMS of
  interaction at Blend 12:00 and 0.20dB at Blend max.
- **Characterise every nonlinear stage as an input→output function**, not a
  table of outcomes at settings. Linear filters commute, so pedal order only
  matters where a linear stage meets a nonlinear one. That needs the
  nonlinearity itself (`ess_ladder` harmonics plus the `levels` probe).
- **Multiband stages** (a crossover, a multiband compressor) split the
  spectrum before acting on it, so their overall curve is not composable. The
  split has to be measured too.
- **Never infer an interaction from an assumed control law.** The EQ Seeker's
  bands appeared not to add in dB by 0.9–3.8dB. With the slider law fitted
  rather than assumed, independent bands predict the combinations to 1.7dB.

## 6. Units and conventions

- dB are 20·log10 of magnitude ratios. dBFS are relative to digital full
  scale at the capture (ZEDi-10 M2, gain +5) unless a field says "send".
- Slider and knob positions are in the units printed on the pedal, or
  `notches` from centre (−5..+5) on the EQ Seeker. Clock positions (9:00,
  12:00) are used for rotary knobs.
- Frequency grids: Farina fields use a 1/12-octave grid from 20Hz
  (`farina_grid_hz`). Legacy fields use third-octave centres
  `1000·2^(k/3)`.
- **Differences under 3dB in a band are treated as equivalent** for tone
  decisions in the source project. That is a decision rule, not the
  measurement resolution, which is 0.01dB for re-amps.

## 7. Pitfalls that produced confident wrong numbers

Each one cost real work in the source project. All of them looked fine.

1. **Single-level sweeps on a stage with gain** (above).
2. **The wrong send level for a pedal.** A drive pedal's response depends on
   its operating point, so a probe too quiet reads a different pedal. Tag
   every capture with its send level so same-level comparisons stay possible.
3. **A reference from a different session.** The Tidal Wave's TW02 reference
   from the previous day differed by 6.6–9.5dB at frequencies the knob under
   test could not reach.
4. **Correlating against the whole ladder locks onto the loudest rung.**
   Search for the first rung only where it can be.
5. **FFT-ing a windowed segment at the wrong length.** Zero-padding a whole
   deconvolution and FFT-ing at 32768 points truncated it to leading zeros,
   which printed a perfectly flat 0.0dB "null".
6. **Gate step counts.** A burst counter that numbered steps from the quiet end
   mislabelled everything once a gate removed quiet steps. Count from the loud
   end, and report missing steps as gated.
7. **mp3 decoding.** soundfile silently under-decoded some VBR mp3s (a 253s
   file decoding as 154s). Captures here are WAV. If you must use mp3,
   use CBR and check the decoded length.
8. **The loop's own headroom read as the pedal's.** It happened four times
   (EQ Seeker, Tidal Wave, Monomyth, EMG; table in `interface/README.md`).
   A limiter anywhere after the stage gives exactly the signature of "the
   stage's boosts run out of headroom": boosts compress at the loud rung,
   cuts pass in full. Before blaming the stage, check the return level
   against the loop's own distortion curve. Better still, capture the same
   probe with the stage bypassed at the same return level.
9. **Harmonic character read from the loudest rung.** The Big Muff read as
   "balanced even/odd" (+0.9dB) at the top rung and −47dB at the quiet ones.
   The capture path was adding even harmonics.

## 8. Stages upstream of the jack (instrument)

The EMG preamp and pickup pan sit before the output jack, so they cannot be
re-amped. The source project measured the preamp with a headphone transducer
laid on the body between the pickups, driving a sweep into the coils
magnetically. The measurement is ratiometric (take divided by an EMG-flat
reference), so the transducer, its coupling, the pickup resonance and the
flux tilt all cancel. Pickup pan cannot be measured that way, because a
damped string has no position-dependent comb. It comes from played takes.
The preamp curves are in `data/equipment/emg-bqc/`, and the string-decay
data in `data/equipment/instrument-trbx305/`.
