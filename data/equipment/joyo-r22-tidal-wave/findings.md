# Joyo R-22 Tidal Wave — findings

Bass preamp / DI with an amp-and-cab simulation: Drive, Blend (dry/wet),
Presence, Treble, Middle (switchable 500Hz / 1kHz), Bass (switchable 40 / 80Hz),
Level, and an XLR DI out (the capture path). Measured 2026-09-15 and 09-16
(TW01–TW34), every other pedal bypassed. Settled knobs (TW02): every tone
control and Level at 12:00, Drive 9:00, Blend 12:00, Middle @500Hz, Bass
@40Hz.

Small-signal numbers are the quietest ladder rung (sent at −63dBFS peak),
Farina route, **against the whole loop bypassed**. Probe send level was
−23dBFS (tag `lad`) unless marked `lad30` (−30).

## Headline numbers

| Property | Value | Evidence |
|---|---|---|
| Settled, vs bypass | −6.9dB at 31Hz, within ±2.6dB from 62Hz–2kHz, **−18.2dB at 3.9kHz**, −3.5dB at 8kHz | TW02 |
| Presence | a peaking control near **3.9kHz**: min ≈ flat, max **+17.6dB** at 3.9kHz (+14 at 2kHz). **At 12:00 it is a narrow notch**, Q≈8, ~−18dB | TW10–13, TW02 |
| Treble | broad, corner ~1kHz, peak ~3kHz: **−13 to +14dB** | TW14–17 (source: raw bins) |
| Middle | broad peaking control, **−17.3 to +19.1dB**, centred exactly on 500Hz or 1kHz by the switch | TW18–21 |
| Bass | broad bell, **−14.7 to +15.3dB**. The 40Hz position peaks at 39–50Hz, the 80Hz position at 79Hz; the two coincide above ~125Hz | TW22–25 |
| Level | flat gain, **−32.7 to +6.6dB**: most of the travel is below 12:00 | TW26, TW27 |
| Tone stack position | **after the Blend**: Treble max at Blend fully dry still gives +10 to +13dB at 2–4kHz | TW28 |
| Blend min (dry leg) | not a bypass: a gentle rising tilt, +2.1dB at 31Hz to +5.3dB at 4kHz vs bypass, linear | TW07 |
| Blend fitted wet fraction | 12:00 = **0.52**, 3:00 = 0.89 (at −23dBFS send). At −30 the fit returns 0.14, because a quieter probe saturates the wet path less | source `blend_check.py` |
| The cab sim (Drive 7:00 fully wet vs dry) | **a −16dB notch at 1kHz**, −10dB at 500Hz, −10dB at 31Hz, −24dB at 8kHz. Linear | TW29 vs TW07 |
| Drive | **a pure pre-clipper gain**, flat across 40Hz–2kHz to ≤0.16dB at every position. Relative to 9:00: 7:00 −5.8, 11:00 +6.6, 1:00 +12.9, max **+29.2dB** (35dB of range) | TW29–TW32 |
| Drive taper | half the travel (7:00→11:00) buys 12.4dB; the last quarter (1:00→max) buys 16.3dB | same |
| Clipping | symmetric-ish and odd-dominant (H3 strongest). Level-dependence across the ladder: 5.2dB at 7:00, 8.9 at 9:00, 14.2 at 11:00, 19.8 at 1:00, **32.1dB at max** (a hard limiter) | TW29–TW32 |
| Loop drift across sessions | TW01 (09-15) vs MUFF01 (09-16), both bypassed: **+0.2dB flat** | TW01 |

### Drive × Blend

Each Blend 12:00 take predicted from the dry take and its fully-wet partner
lands on a wet fraction of 0.45–0.58 at every Drive (band error 1.2–2.1dB), so
Blend and Drive separate. Measure Drive fully wet and model the crossfade.

## Read with care: the loop's own headroom

The top ladder rung was sent at −23dBFS peak, and through the bypassed loop
it already returns at **−13.4dBFS**, where the loop itself distorts at about
5% (`interface/README.md`). Every boost pushes it further. Treble max returns
**−4.0**, Middle max −3.8, Bass max −3.2dBFS. So the source project's
statements that **"the boost side runs out of headroom at the top rung"**
(Treble, Middle, Level, Presence) are **not separable from the loop**, and
should not be read as properties of this pedal. The same goes for the
Presence notch "filling in at real levels" (−13.8dB small-signal, −3.8dB at
the top rung): distortion products from anywhere in the path fill a notch.
Use rungs 0–2. The model is fitted on all five, so its top-rung behaviour
carries the loop with it.

## Model (`models/wiener_hammerstein/`)

`wet = H2 · f(k_drive · G · H1 · x)`: highpass at ~74Hz → asymmetric soft
clipper (negative ceiling 0.79 of positive, small bias) → complex
post-filter H2 (cab sim, tone stack at settled, loop). Fitted on the waveform
of the five fully-wet Drive takes, phase included. The dry leg and the 12:00
crossfade (a = 0.46, b = 0.32, wet delayed 4.8 samples) come from TW07 and TW02.

| check | error (octave bands per rung, dB RMS, one gain offset per take) |
|---|---|
| Fitted Drive takes 7:00 / 9:00 / 11:00 / max (this port) | 1.35 / 1.40 / 1.64 / 2.58 |
| Held-out Drive 11:00, 1:00 (source, cross-validated) | 2.17, 2.63 |
| Blend 12:00 at Drive 7:00 / max, never fitted (this port) | 0.24 / 2.39 |
| Blend 12:00 settled (calibration take) | 0.30 |
| Harmonic levels | **poor, 13dB or worse.** Use it for level and response, not distortion spectra |

Hypotheses tested and refuted in the source project (keep them refuted unless
there is new data):
- **A Drive-independent clean path in parallel with the clipper.** On the
  quiet rungs any such path measures at −46dB, and the two-path fit degenerates
  into a 135–200Hz sliver.
- Six earlier shaper forms fitted to magnitudes. They failed on phase: the cab
  sim carries 6.7ms of group-delay dispersion.

## Superseded

- "Blend 12:00 is 14% wet": measured at the wrong send level (−30). It is 52%.
- "Presence notch is a +8dB spike at 4kHz in every take": the notch was in the
  shared reference (TW02), not in the takes.
- TW11 was first recorded at Presence 3:00 while labelled 9:00. Two adjacent
  settings that measure identically are a knob that did not move. The
  current TW11 is correct.
