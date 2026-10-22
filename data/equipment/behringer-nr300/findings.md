# Behringer NR300 — findings

Noise reduction pedal with Threshold and Decay knobs, wired as a 4-cable loop
(it detects on the bass entering the loop and gates the loop's return).
Measured 2026-09-15: one gate-off reference (NR01) and seven settings
(NR02–NR08), each re-amped with the same performance and the 110Hz level-steps
probe, with every other pedal bypassed. Take IDs are the citations.

**Level scale.** Every level here is dBFS at the capture, where the bass played
normally peaks at **−14.0dBFS** and runs at about −33dBFS RMS (the music
reference, NR01). So "−60dBFS" means 46dB below a normal playing peak.

## Headline numbers

| Property | Value | Evidence |
|---|---|---|
| Type | **broadband downward expander**, not a filter: gated frames show the same −16dB ±2 from 20Hz to 4kHz | model + coherent transfer on gated frames |
| Range (floor) | **−17.0dB**, identical on every fully gated step of every setting | NR05, NR06 level steps |
| Threshold, by knob (fitted, peak detector) | min **−70**, 9:00 **−61**, 12:00 **−45**, 3:00 **−32**, max **−24**dBFS | NR03, NR02, NR04, NR05, NR06 |
| Threshold law | flat over the lower half of the knob (~10dB from min to 9:00), then ~37dB over the upper half | same |
| Expansion slope below threshold | 1.7dB of cut per dB under (then clamped at −17) | settled fit |
| Hysteresis | 5.5dB (an open gate closes 5.5dB lower than it opens) | settled fit |
| Attack / hold / release | 16ms / 136ms / **101ms (Decay 7:00), 569ms (12:00), 1,856ms (max)** | NR02, NR07, NR08 |
| Pass-through gain, gate open | **−0.20dB**, flat (−0.24 at 31Hz to −0.09 at 250Hz on musical frames) | all level steps, NR03 |
| Polarity | **inverted** when engaged, at every setting | every NR0x vs NR01 |
| Detector | peak-sensing (frame peak, 7.9ms release) fits as well as RMS on music and better on the level steps | validation.json |

### Threshold, as the level steps show it

Gain per 110Hz step against the gate-off reference. Step input levels (frame
RMS): −53.4, −47.4, −41.4, −35.4, −29.4, −23.5, −19.5, −16.8dBFS.

| setting | −53.4 | −47.4 | −41.4 | −35.4 | −29.4 | louder |
|---|---|---|---|---|---|---|
| Thr min (NR03) | −0.2 | −0.2 | −0.2 | −0.2 | −0.2 | −0.2 |
| **Thr 9:00 (NR02)** | −0.2 | −0.2 | −0.2 | −0.2 | −0.2 | −0.2 |
| Thr 12:00 (NR04) | **−12.5** | −0.4 | −0.2 | −0.2 | −0.2 | −0.2 |
| Thr 3:00 (NR05) | **−17.0** | **−17.0** | **−17.0** | −3.1 | −0.3 | −0.2 |
| Thr max (NR06) | **−17.0** | **−17.0** | **−17.0** | **−17.0** | −7.4 | −0.2 to −0.3 |

### On a real performance

The same ~218s fingerstyle performance (*Linkin Park – With You*), 5ms frames,
change against the gate-off reference. Reference frame levels: 1st percentile
−98.3, 10th −94.1, 25th −87.2, 50th −43.7, 75th −36.3, 95th −25.5dBFS.

| setting | 1st | 10th | 25th | 50th | 75th | 95th |
|---|---|---|---|---|---|---|
| Thr min | −5.3 | −3.5 | −4.2 | −0.2 | −0.2 | −0.2 |
| **Thr 9:00** | −5.2 | −3.8 | −6.1 | −0.2 | −0.2 | −0.2 |
| Thr 12:00 | −5.0 | −3.6 | −6.4 | −0.2 | −0.2 | −0.2 |
| Thr 3:00 | −4.9 | −3.8 | −6.5 | **−1.5** | −0.4 | −0.4 |
| Thr max | −4.9 | −3.7 | −6.2 | **−13.5** | **−3.6** | −1.6 |
| Dec 12:00 | −5.0 | −3.8 | −5.8 | −0.2 | −0.2 | −0.2 |
| Dec max | −4.4 | −2.9 | −4.7 | −0.2 | −0.2 | −0.2 |

- **Up to 12:00, played notes pass untouched** (median −0.2dB) and rests drop
  4–6dB. Rests don't drop the full 17dB, because about −97dBFS of the
  re-amp loop's own noise is added *after* the gate.
- **From 3:00 the gate starts eating notes**; at max the median frame loses
  13.5dB.
- **Decay changes only the tails.** Release goes from 0.1s to 1.9s across the
  knob, but on played notes all three Decay settings measure the same.

The source project's published version of this table used a different frame
analysis. Its medians agree (−0.18dB at 9:00) but its tails differ by 1–2dB.
This table is the one reproducible from `measurements/envelopes.npz`.

## Polarity, and why it matters downstream

The engaged pedal inverts the signal. Gate off (NR01) it does not. On its own
that is inaudible, but the capture path here clips positive excursions near
−14dBFS. The performance's largest peaks are positive, so the gate-off capture
flat-tops them, and every engaged capture carries them on the negative side
instead (NR01: +peak −14.0, −peak −15.9; NR02: +peak −16.2, −peak −11.5). Any
asymmetric stage downstream (a clipper, a DI with asymmetric headroom) sees
the opposite half-cycle depending on whether this pedal is engaged.
`apply_model(..., invert=True)` reproduces it.

## Model (`models/expander/`)

Fitted to the frame envelopes in `measurements/envelopes.npz`. The settled
setting is fitted on the first half of the performance and scored on the
second, which it never saw. The other settings each refit one parameter.

| | envelope error, dB RMS |
|---|---|
| Settled, played frames (> −60dBFS), held-out half | **0.18** |
| Settled, all non-rest frames, held-out half | 1.07 |
| Other settings, played frames | 0.16–1.47 (worst: Thr max) |
| Level steps, never fitted, thr-moving settings | 0.7–1.3 per step |
| Transition frames (−85 to −60) | 3.2–4.0 |

Transition and rest frames are where the loop's own noise and the gate's
timing both matter. Treat the model as good to ~0.2dB on notes, and as
qualitative in decays.

The parameter set is not unique. Refitting reproduces the source project's
errors to within 0.03dB, but its threshold and slope trade against each other
(source: thr −62.3, slope 2.86; this fit: −60.5, 1.71), along a flat valley.

## Capture contaminant

NR02 and NR05 carry a tonal interferer at ~415Hz and ~829Hz on played frames,
uncorrelated with the input and absent from the takes recorded between and
after them. It is in the recording, not the pedal: NR02's 1kHz octave reads
+8.3dB in power but −0.6dB in the coherent transfer. Those two takes'
`musical_frames_band_gain` power figures should not be read as the pedal.
Use NR03, NR07 or NR08, which behave identically on played frames.

## Superseded

- **"Mid +3.27dB, brilliance +6.67dB"** from a whole-take transfer function:
  those bands sat 60–105dB below the music, so it was noise measuring
  noise, plus the interferer above. A gate has to be measured on level,
  frame by frame, not by spectrum.
- **"Decay does nothing measurable"**: true on played notes, but the knob moves
  the release time 18x. It acts only on decays into rests.
