# EHX Deluxe Bass Big Muff Pi — findings

Fuzz with Sustain, Tone, Blend (dry/wet), Volume, Gate, and a switchable
crossover (HPF on the fuzz path, LPF on the clean path). Measured 2026-09-16
to 09-20 (MUFF01–MUFF37), every other pedal bypassed. Settled (MUFF02): Tone
5:00 (= max), Sustain 12:00, Blend 12:00, Volume 5:00, Gate 9:00, crossover
out (HPF 11:00, LPF 2:00 when engaged). Probes sent at −23dBFS (`lad`).

## Architecture, measured

```
   in --+-- LPF ----------------------------- clean lows --+
        |   ~100Hz .. off                                  +-- Blend -- Volume -- out
        +-- HPF -- Sustain -- Clip -- Tone ---------------+    (12:00 = 0.33-0.45 wet)
            ~140Hz .. ~1.4kHz
```

- The tone stack is **after the clipper**: the odd harmonics are identical, to
  0.1dB, across Tone min / 9:00 / 12:00.
- The HPF is **before the clipper**: Blend max with the crossover engaged
  (MUFF31) settles it.
- Both crossover filters are second-order and resonant (+10dB peaks flanking
  their corners small-signal), which looks like a state-variable pair.

## Headline numbers

| Property | Value | Evidence |
|---|---|---|
| Settled vs bypass | a fuzz: **+11.5dB at 500Hz and −23dB at 31Hz small-signal, near-flat (±1.4dB) at the −23dBFS rung**. Median level spread 8.4dB | MUFF02 |
| Clipping character | **symmetric: odd-dominated by 13–47dB**, H3 largest. Even−odd −47dB at the settled Sustain fully wet. Read from the quiet rungs | MUFF07–10, MUFF16 |
| Sustain | gain plus saturation. min→9:00 +10dB, 9:00→3:00 +14 to +20dB, 3:00→max ~+1dB. Total harmonics −48 → −27 → −12.5 → −13.6dB. **Useful travel ends at 3:00** | MUFF07–10 |
| Tone (end to end, fully wet) | **mostly a bass cut**: −15dB at the bottom octave, +5.9dB at 4kHz, 21dB of tilt. Taper: 9:00 does nothing (−0.6dB of tilt), 12:00 gives 17% of the range, the rest is in the upper half | MUFF11–13, MUFF16 |
| Tone × Sustain | independent fully wet (0.20dB interaction RMS). At Blend 12:00 the same four corners read **9.28dB**: the dry path makes every wet control look interactive | MUFF03–06 vs MUFF26–29 |
| Blend | fitted wet fraction at 12:00: **0.325** on the ladder (band error 0.99dB, worst −2.1dB in the top octave). The source project's chain uses 0.445 at playing level | MUFF14/02/16 |
| Blend changes dynamics too | removing the dry path makes the pedal **21dB louder on quiet input and 12dB quieter on loud input** | MUFF16 vs MUFF02 |
| Gate | threshold only; decay is fixed at ~0.18s by the circuit. Settled 9:00: rests −99.3 vs −93.8dBFS at min (**5.5dB quieter**), every step passes. Max deletes the four quietest of eight steps | MUFF17, MUFF02, MUFF18 |
| HPF travel (crossover in) | corner ~140Hz (min), ~200Hz (11:00), **~1.2–1.5kHz (max)**: most of the travel is in the upper three quarters | MUFF32, MUFF33 |
| LPF travel | corner ~100Hz at min (12–15dB/octave, 2nd order), ~2kHz at 2:00, **off at max** (flat to 0.8dB) | MUFF34, MUFF35 |
| Crossover vs distortion | the crossover is not inert: about 30dB less distortion at 110Hz with it engaged | MUFF19 |
| Re-amp reproducibility | **0.01dB** median after moving both knobs away and back (MUFF07 vs MUFF27, MUFF10 vs MUFF29) | — |
| Noise | the rig's noisiest pedal: **+5.3dB** over a −92.9dBFS no-pedal floor (source noise pass, 2026-08-31). Its own gate takes 5.5dB of that back | — |

## Read with care

- **Read harmonic character from the quiet rungs.** The source project's
  first reading (even−odd +0.9dB, "balanced") came from the loudest rung,
  where the capture path clips and adds even harmonics. That is the same
  re-amp loop limit described in `interface/README.md`.
- Every small-signal resonance and boost here **flattens with level**. That is
  the fuzz compressing, but at the top rung (returns −14dBFS and above) the
  loop contributes too.

## Model (`models/circuit/`)

A circuit simulation of the Black Russian Big Muff core, which EHX names as
the Deluxe Bass's basis: four 2N5088 stages, 1N914 clippers through 47nF, the
22k/3n9/10n/22k tone stack, Sustain and Tone as real pots. It uses a DK-method
nodal solver at 2x oversampling. Nine values were fitted by CMA-ES on four
Blend-max takes:

| fitted | vs Black Russian |
|---|---|
| coupling caps | x1.36 |
| clip / Miller caps | x1.04 / x0.98 (stock) |
| tone C10 (3n9) / C11 (10n) | x0.79 / **x0.48**: the bass voicing is in the tone stack |
| transistor beta / diode n | ~550 / 2.04 |
| Sustain pot | 12% of resistance at half rotation (audio taper) |

| check | error |
|---|---|
| Probe fit (textbook values → fitted) | 2.87 → **2.09dB** |
| Held-out knob settings, ladder (source) | 0.87–1.85dB |
| Level steps, fundamental (this port) | 0.26–0.97dB on 8 of 9 settings, 2.16 on MUFF28 (Sustain max, Tone min) |
| Played-performance re-amps, never fitted (source) | **0.69dB** settled, 1.08 Tone max / Blend max, 1.39 Tone min / Blend max. The earlier black-box model scored 1.77 / 3.67 / 3.08 on the same three |

Not modelled: the crossover, the gate (open), the Deluxe's input buffer and
output stage (flat gains). Blend is a crossfade against a flat dry path.

## Superseded

- "Even−odd +0.9dB, the Muff clips asymmetrically": a loud-rung capture
  artefact. Quiet rungs: −47dB.
- "Tone and Sustain interact strongly": the dry path does it at Blend 12:00.
  Fully wet they are independent.
- "The crossover is inert at minimum" (a 2026-08-28 inference, never measured):
  wrong, see MUFF19.
- A Wiener-Hammerstein black-box model (pre-filter, shaper, post-filter):
  2.2dB on music near the settled point and worse away from it, because it has
  no idea what Sustain and Tone physically are. Replaced by the circuit model.
