# Yamaha TRBX305 (the instrument) — findings

What reaches the preamp: strings, pickups, pickup position and plucking. These
come from played takes (no re-amping is possible ahead of the output jack),
so the resolution is the ~0.8dB take-to-take floor, not 0.01dB.

Instrument facts (scale, strings, pickup geometry, woods) are in `rig.md`.

## String decay — ordinary, and the string's own

`measurements/string_decay.json`: 3,313 per-partial exponential fits from six
played takes (R25, R27 per-note scales; R33–R36 pluck block).

| band | median decay | T60 |
|---|---|---|
| 125–250Hz | 11.5dB/s | ≈5.2s |
| 500Hz–1kHz | 21.8dB/s | |
| 1–2kHz | 33.2dB/s | |
| 2–4kHz | 40.5dB/s | ≈1.5s |

- The rate grows roughly as √f. That is the textbook air-viscosity signature,
  normal for steel roundwounds (D'Addario, about a month old at the time).
- For the 5th harmonic and up, the rate is the same within x0.97–1.09
  across fingers or pick, neck or bridge plucking spot, neck or bridge
  pickup, and a retake three weeks later.
- **Ends of the string take about a fifth.** A 12th-fret note (terminating on
  a fret) decays x1.18 as fast as the open string at the same frequency.
  Pure end losses would give x2, pure along-string losses x1. The G string is
  the exception (x0.87), which could be a neck resonance.

## Where the high frequencies go

- **The attack spectrum falls 15–19dB/octave above 250Hz** (fingers ~19,
  pick ~15). An ideal plucked string sensed by velocity falls ~6dB/octave.
  Neither the pluck position nor the tool explains more than ~4dB/octave of
  the difference. **Unexplained.** The suspects left are the pickup's
  absolute response (the injection sweeps are ratiometric, so they can't see
  it), wound-string stiffness, and the release of the finger or pick.
- A "−30dB signal ceiling" near 370–415Hz was once blamed on pickup aperture.
  That is **ruled out by geometry**: the 17mm coil spacing costs under 1dB at
  400Hz. The ceiling turned out to be a metric artefact: a −30dB threshold on
  a ~25dB/octave slope, quantised to whole harmonics, barely moves when band
  levels change by 6–9dB. **Read band levels, not a −30dB ceiling.**
- **Pick vs finger, same spot** (R33 → R35): at the attack (30–180ms) the pick
  lifts 500Hz–1kHz +8.7dB, 1–2kHz +10.6dB and 2–4kHz +7.4dB relative to the
  note's peak. In the sustain (150–950ms), 500Hz–2kHz is still +6–9dB.
- **Bridge vs neck plucking spot** (R33 → R34): a low-mid tilt (+8dB at
  250–500Hz relative to the peak, +4–6dB at 500Hz–1kHz, +2–3dB at 1–2kHz,
  nothing above 2kHz), mostly from a thinner fundamental. No new treble.
- The pickups' dual-coil layout (coil centres 17mm apart along the string)
  puts a null at 34mm wavelength: ~1.6kHz on B0, 2.1kHz on E1, 2.8kHz on A1.

## Pickup pan

Pan is a comb filter, not a tone control. Both extremes measure above the
centre position in 250–400Hz and above 2kHz, which only cancellation at the
centre can produce. See `../emg-bqc/findings.md`, "Pickup pan".

## Scale length

At a fixed pluck distance from the saddle, the spectral roll-off point scales
with string length. A 35" scale buys ~3%, and a fanned 37" B ~9% on the B
string (~0.1 octave). The hand position matters far more: plucking 100mm from
the saddle instead of 138mm is a ~38% lift.
