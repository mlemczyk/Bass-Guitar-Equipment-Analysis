# The re-amp loop

Every pedal in this dataset was measured by playing a probe out of the
computer, through the pedal, and back in. Each result is a ratio against a
reference capture through the same loop, so the loop's own response divides
out. The loop still matters in three ways: its noise floor, the level at
which it starts to distort, and how much it drifts between sessions.

## Path

```
computer (WDM, 44.1kHz) → Allen & Heath ZEDi-10 USB → ST2 → aux send (100%)
  → pedalboard input
  → [NR300 send: BC-1X → Strobostomp tuner → Monomyth → Big Muff → EQ Seeker → volume pedal]
  → NR300 return → Joyo R-22 Tidal Wave → its XLR DI out
  → ZEDi-10 M2 (XLR, gain +5, pinned) → USB → computer
```

Every stage not under test is bypassed. The tuner's buffer and the volume
pedal are always in the path, including in every reference capture.

## Measured

| Property | Value | File |
|---|---|---|
| Round trip, everything bypassed | +0.6dB at 62Hz, +0.8 to +1.1dB from 125Hz to 8kHz, −0.8 at 31Hz, −2.1 at 20Hz, +0.2 at 16kHz | `measurements/LOOP-NULL.json` (L01) |
| Noise floor, silence through the loop | −100.1dBFS RMS, 20Hz–20kHz | `measurements/LOOP-NOISE.json` (L03) |
| Loop gain at M2 +5 | +8 to +10dB. A −23dBFS-peak probe returns at about −13.4dBFS peak | source project calibration `L02` |
| **Distortion vs return level** (110Hz, everything bypassed) | 0.04% at −26.6, **0.21% at −20.6, 0.72% at −16.7, 5.5% at −14.1dBFS** return peak | `measurements/LOOP-LEVELS.json` |
| Take-to-take reproducibility, same session | 0.01dB (source project, measured twice on the Big Muff and once on the Monomyth) | — |

L03's source-project figure was −94.1dBFS. The −100.1 here is the same
capture band-limited to 20Hz–20kHz, so the difference is DC and subsonic
content.

## The loop distorts before the bass's own peak level

The bass itself peaks at about −13dBFS at M2 when played. On this loop, a
steady tone returning at −14dBFS already carries 5.5% THD. The source project
did not know this, and it changes how to read some of its results:

- **Any boost measured at the top ladder rung is compressed by the loop,
  not by the pedal.** This is shown directly for the EQ Seeker (its
  `findings.md`). A boosted take there returns at −9dBFS from the loudest
  rung, and the loop takes about 2.8dB off it.
- The same check is owed to every result in the source project that reads
  "boosts limit before playing level" (the Monomyth's EQ sliders) or "runs out
  of headroom" (the Tidal Wave's tone stack). Those pedals are not in this
  repository yet. When they are, compare each take's `return_peak_dbfs`
  against the table above before attributing compression to the pedal.

The distorting stage is somewhere in the return path: volume pedal, NR300
return, the Tidal Wave's DI, or M2's preamp. Which one is not known.

**That return path is also the live signal path.** Only the send side
(computer → aux → pedalboard input) is specific to re-amping. So on this rig a
pedal that pushes the signal past about −17dBFS at the mixer distorts while
being played too, just not inside that pedal. The source project attributed
the effect to the pedal in four places. Each one has the same signature
(boosts compress, cuts pass, and only at high return levels), and each is
re-read in that pedal's `findings.md`:

| source finding | pedal | re-read |
|---|---|---|
| "output stage compresses boosts above −30dBFS" | EQ Seeker | the loop (shown directly with the level-steps probe) |
| "boost side of the tone stack runs out of headroom" | Tidal Wave | top-rung returns −3 to −8dBFS: not separable from the loop |
| "every EQ boost is capped at +4 to +6dB, cuts deliver 96–99%" | Monomyth | boosted top rungs return −5.5 to −9.8dBFS; on real material the EQ acts at its small-signal response |
| "the preamp clips at Mid +5" | EMG BQC | played take peaked −8.9dBFS at M2; fresh 19.3V cells changed nothing |

## Y-split (raw tap) validation

`measurements/YSPLIT-Y0*.json`. Splitting the bass cable to a second mixer
input, to record a raw re-ampable arm alongside the board:

- method floor (Y05 repeating Y02 with nothing touched): **0.07dB**
- Y-split into M3's line input: **−0.94dB**, broadband and resistive. M3's
  −20dB pad did not change the loading.
- Y-split into **M1 with Hi-Z engaged: +0.07dB, i.e. nothing**. That is how
  every dual-tap take in the source project was recorded.

**Rule for new measurements:** keep the return below about −21dBFS peak for
under 0.2% added THD. For a sweep ladder sent at −30dBFS peak (rungs
−70..−30), that means a stage under test may add at most about +8dB before the
top rung is affected.

## Session drift

The reference capture is re-recorded in each session, because the loop moves
between sessions:

- **2026-09-15 to 09-20:** stable. Takes recorded on 09-20 against the 09-15
  flat reference show offsets of no more than 0.5dB (EQ Seeker SEEK27/28).
- **2026-10-18:** the flat reference came back +7.8dB hotter at the −60dBFS
  rung, and level-dependent. Relative to 09-15, the quietest rung lost 9dB
  above 5kHz, and the louder rungs lost up to 10dB of top end. Something in
  the loop that evening behaved like a dynamics stage. **Within** that
  session, ratios are consistent to 0.0dB across all five rungs (EQ Seeker
  SEEK29), so same-session comparisons from that date are sound, and
  cross-session ones are not.
