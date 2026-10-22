# The rig

The equipment this data was measured on, as it stood 2026-10-21. A pedal's
own folder holds its measurements. This page holds the context that shapes
all of them.

## Instrument

- **Bass:** Yamaha TRBX305, 5-string, standard tuning B0-E1-A1-D2-G2, 34"
  (864mm) scale, 24 frets. Solid mahogany body, 5-piece maple/mahogany
  bolt-on neck, rosewood fingerboard, high-mass die-cast bridge, Graph Tech
  nut.
- **Strings:** D'Addario steel roundwounds, custom .135 low B, fitted
  ~2026-09-10.
- **Pickups:** stock Yamaha M3 ceramic dual-coil humbuckers, 2-lead, ~5kΩ
  DCR, 2mm height. Pole pieces 10mm, coil centres 17mm apart along the
  string. As a two-point sum, that gives a −3dB point at 68mm wavelength and
  a null at 34mm: ~780Hz/1.6kHz on B0, ~2.5/5.0kHz on G2.
- **Preamp:** EMG BQC HZ (Bass, Mid, MidFreq, Treble, pickup pan; treble DIP
  switches left OFF/OFF), 18V from two 9V LiPo batteries in series.
  Measured curves will be in `data/equipment/emg-bqc/` (not yet published).
- **Playing:** fingerstyle, fingertips, short nails, plucked over the neck
  pickup ~138mm from the saddle. That holds for every played take before
  the pluck block (R33–R40). The pluck position's comb filter is in every
  played measurement.
- **String decay** (3,313 partial fits, played takes): median 11.5dB/s at
  125–250Hz, 21.8 at 500Hz–1kHz, 33.2 at 1–2kHz, 40.5 at 2–4kHz, so T60 falls
  from ≈5.2s to ≈1.5s, growing roughly as √f. It is the same for fingers and
  pick, and the same at both pluck spots. A 12th-fret note decays x1.18 as
  fast as the open string at the same frequency.
- **Attack spectrum falls 15–19dB/octave above 250Hz** (finger vs pick).
  That is steeper than an ideal plucked string sensed by velocity (~6), and
  neither pluck position nor tool explains more than ~4dB/octave of the
  difference. Unexplained.

## Signal chain (pedal order)

```
Bass → Behringer NR300 (noise gate, 4-cable send loop):
         Boss BC-1X (multiband compressor)
         → Peterson Strobostomp (tuner, buffered, always on)
         → Joyo R-26 Monomyth (bass overdrive with 6-band EQ)
         → EHX Deluxe Bass Big Muff (fuzz with crossover)
         → Donner EQ Seeker (10-band graphic EQ)
         → Boss volume pedal (parallel pot mod; played, never set)
       → NR300 return
     → Joyo R-22 Tidal Wave (preamp / DI with cab sim)
     → Allen & Heath ZEDi-10, channel M2 (XLR, gain +5)
     → USB → Windows 11
```

The **Tidal Wave bypassed still passes its DI out**, uncoloured, so it is in
every capture. The **tuner and volume pedal are always in the path**,
including in every reference capture, so they divide out of every ratio. They
are part of the baseline, not unmeasured stages.

## Interface

- **Allen & Heath ZEDi-10** (USB, 44.1kHz in normal use). M1 can take a
  Y-split raw tap off the bass (Hi-Z, +18, pad −20dB). M2 is the pedalboard
  return at gain **+5, pinned**: every re-amp calibration assumes it. ST2
  carries computer playback. No ASIO.
- M1 floor −82.9dBFS, mains band −86.9 (unbalanced Hi-Z run). An unbalanced,
  unterminated mixer input was the noisiest state found anywhere in the rig
  (−88.65dBFS).
- The Y-split onto M1's Hi-Z input loads the bass by +0.07dB (nothing). On a
  line input (M3) the same split cost −0.94dB, broadband and resistive.
- Re-amp loop measurements: `interface/README.md`.

## Power

All pedals daisy-chained from one Roland supply. Not a ground-loop source:
unplugging pedals from power made the rig louder, not quieter (buffered bypass
keeping the path low-impedance). Per-pedal added noise over a −92.88dBFS
no-pedal baseline (2026-08-31): Big Muff +5.3dB, BC-1X +1.9dB, Monomyth and
EQ Seeker nothing measurable. A ~120Hz-spaced hum family lives in the
pedalboard's path at −99 to −114dBFS, band-limited.

## Not measured, deliberately

- **Peterson Strobostomp:** always on, so it is inside every reference.
- **Boss volume pedal:** played per song, so it has no setting to measure. It
  is in the loop, in every capture.
- **The recording room and the monitoring chain** (powered headphone amp,
  Beyerdynamic DT 770 Pro X): not in the capture path.
