# Boss BC-1X — findings

Bass compressor (Threshold, Ratio, Release, Level; Boss "MDP" multiband
processing). Measured 2026-09-16 to 09-29 by re-amping, with every other
pedal bypassed. The settled knobs (BC01) are Threshold, Ratio and Release at
12:00, Level 11:00. Take IDs are the citations. Every response is against the
whole loop bypassed (`reference` in each capture).

**Level scale:** dBFS at the capture, where normal playing peaks at about
−14dBFS.

## Headline numbers

| Property | Value | Evidence |
|---|---|---|
| Below threshold | **+7.7dB flat**, 40Hz–8kHz (makeup gain) | BC01 ladder, rung 0 |
| It is multiband | as an 80Hz tone rises 26dB at the output (40dB in), probe tones at 437 / 1249 / 3527Hz move only **1.0 / 0.5 / 0.5dB** | BC01 twotone |
| Bands (model) | split at **~311Hz**, 4th-order slopes. Low band: threshold −38.8, ratio 2.8:1, knee 14.5dB. High band: threshold **−48.9**, ratio 2.9:1, knee 15.5dB | ladder fit |
| Same ratio, earlier threshold up top | so a sweep shows highs "compressed harder": at the −23dBFS rung, −6dB at 80Hz but −14.9 at 8kHz | BC01 ladder, rung 4 |
| Static curve at 110Hz | gain vs bypass +7.7 → +7.3 → +5.1 → +1.6 → −1.8 → −4.2 → −5.9dB across steps sent −52 to −15dBFS | BC01 levels |
| Program dependence | plucked notes are compressed **2.0–2.5dB more** than RMS-matched steady tones at −24 and −14dBFS input. The bypassed control take shows 0.0 and −0.25 | BC01 vs BC15 plucks |
| Time constants (model) | low band: attack 1ms, release 5ms, RMS detector 60ms. High band: attack 1ms, release **381ms**, RMS detector 3ms. Peak follower 3.8ms | music fit |
| Brightening on music | with compression active, the 1–16kHz octaves gain **5–7dB more than the lows** relative to bypass (BC01). The pedal compresses bass energy and leaves the highs | BC01 music |
| Polarity | not inverted | all music captures |

## Controls, on a played performance

Same ~218s fingerstyle performance (*Linkin Park – With You*) through every
setting. Change in 5ms frame level against bypass, by percentile, and overall
RMS gain:

| setting | 1st | 10th | 25th | 50th | 75th | 95th | RMS gain |
|---|---|---|---|---|---|---|---|
| **settled (BC01)** | +5.9 | +5.4 | +6.6 | +3.6 | +3.7 | +0.6 | +1.1 |
| Threshold min (BC02) | +6.0 | +5.3 | +6.5 | −5.9 | −5.3 | −9.5 | −8.5 |
| Threshold 9:00 (BC03) | +5.8 | +5.3 | +6.5 | −1.6 | −1.2 | −4.7 | −4.0 |
| Threshold 3:00 (BC04) | +5.9 | +5.4 | +6.6 | +7.5 | +7.6 | +6.3 | +6.0 |
| Threshold max (BC05) | +6.0 | +5.4 | +6.6 | +7.6 | +7.5 | +6.3 | +6.1 |
| Ratio min (BC06) | +6.0 | +5.4 | +6.6 | +7.5 | +7.6 | +6.3 | +6.1 |
| Ratio max (BC08) | +5.9 | +5.4 | +6.5 | +3.7 | +4.1 | −0.3 | +0.5 |
| Release min (BC09) | +5.9 | +5.3 | +6.5 | +3.7 | +3.7 | +0.8 | +1.2 |
| Release 3:00 (BC10) | +5.9 | +5.3 | +6.4 | +3.2 | +3.4 | +0.3 | +0.8 |
| Release max (BC11) | +5.9 | +5.2 | +5.4 | +1.1 | +1.1 | −1.1 | −0.9 |

- **Threshold 3:00, Threshold max and Ratio min are the same state**:
  compression off, the makeup gain left (+6 to +7.6dB on every percentile).
  The Threshold control's whole useful range lies between min and about 1:00.
  12:00 sits on its steepest part.
- **Threshold min compresses hardest**: the 95th percentile drops 9.5dB.
- **Release is a smooth control.** The low percentiles stay put while the loud
  ones fall as release lengthens.
- The 1st–25th percentiles rise ~6dB on every setting. Those are rests and
  noise, lifted by the makeup gain. Read compression from the 50th–95th.

The source project's published version of this table normalised every take
to equal RMS. This one does not. Subtract the RMS-gain column to compare.

## Model (`models/twoband/`)

A two-band split compressor with a hybrid RMS/peak detector, per-sample
gain, and the settled knobs only.

| check | error |
|---|---|
| Static curves, ladder (one / **two** / three bands) | 2.50 / **0.91** / 0.64dB RMS. The third band adds little, and its top two bands come out near-identical |
| Music envelope (dynamics fitted here) | 1.85dB RMS, played frames |
| Plucks envelope (**held out**) | 1.14dB RMS; crest error +0.14dB |
| BC07 (Ratio 3:00), ratios refit only | 1.18dB on its ladder |

`validate.py` re-runs the published model on the captures and reproduces
the source project's figures to 0.001dB.

Detector variants on the same static curves (source project): peak gives
music 2.32 / plucks 1.45 / crest +0.36; RMS gives 1.77 / **0.86** / +4.60;
**hybrid** gives 1.85 / 1.14 / **+0.14**. Hybrid was adopted because it gets
both the envelope and the crest roughly right.

**Two traps worth knowing if you build your own model:**
- **Ratio cannot be identified from music.** Fitting the static curves on a
  bass performance sends the ratios to 6–238:1 for ≤0.3dB of envelope
  improvement, because bass leaves the upper band nearly empty. Use a sweep.
- **Frame-held gain is a zipper.** Holding a per-frame gain with
  `np.repeat` read as +12.9dB of presence on music. Compute gain per sample.
- The model's levels are absolute. Feeding it audio normalised 9dB lower than
  the capture under-drives it, and that error was larger than the
  multiband-vs-broadband difference.

## Open

- **A broad +4dB bump at ~380–500Hz** on played frames when compression is off
  (BC04/05/06: 500Hz octave +11.4 against +6.3 for the lows, coherent
  +8.8), smaller at the settled setting. It is not narrowband, so it is not the
  415Hz interferer found in the NR300 captures. No ladder exists at those
  settings to check it against a sweep. Unexplained.
- Level (BC12–BC14) was planned and never recorded.

## Noise

The source project's noise pass (2026-08-31) found the BC-1X adds **+1.9dB**
over a −92.9dBFS no-pedal floor at its settled knobs: the makeup gain lifting
whatever arrives.
