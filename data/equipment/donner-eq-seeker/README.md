# Donner EQ Seeker

10-band graphic EQ pedal: bands at 31.25, 62.5, 125, 250, 500Hz, 1, 2, 4, 8,
16kHz, plus a Level slider. One unit, powered from a daisy-chained Roland
9V supply. Measured 2026-09-15 to 2026-10-18.

**Findings: [`findings.md`](findings.md).** In brief: centres on nominal,
+13 to +16dB at +5, symmetric cut and boost, a very nonlinear slider law
(−3 → −4 is a 9dB cliff), linear and noise-free when flat, −1.0dB insertion
loss. The boost "compression" previously reported was the measurement loop.

## Settings vocabulary (`settings` in each take)

```json
{"engaged": true, "level_slider": 0,
 "band_sliders": {"31.25": 0, "62.5": 0, "125": 0, "250": 0, "500": 0,
                  "1k": 0, "2k": 0, "4k": 0, "8k": 0, "16k": 0}}
```

Slider positions are **notches from the centre detent, −5..+5**. `engaged:
false` is footswitch bypass (sliders irrelevant, `null`).

## Takes

| take | setting | probes | reference |
|---|---|---|---|
| SEEK01 | bypassed | ess | SEEK02 |
| SEEK02 | engaged, all 0: **the flat reference** | ess, ess_ladder ×2 sessions | SEEK01 / itself across sessions |
| SEEK03–12 | one band at +5 (31.25Hz … 16kHz in order) | ess_ladder (+ superseded ess, ess_lin) | SEEK02 |
| SEEK13, 14 | 125Hz −5, 1kHz −5 | ess | SEEK02 |
| SEEK15, 24, 25 | 500/1k/2k at −2, −3, −4 | ess_ladder | SEEK02 |
| SEEK16, 27, 28, 29 | 125+250 at −5, −2, −3, −4 | ess_ladder | SEEK02 (SEEK29: SEEK02 of 2026-10-18) |
| SEEK17 | all ten at +2 | ess_ladder | SEEK02 |
| SEEK18, 19 | Level +5, −5 | ess (SEEK18 unusable: loop distortion) | SEEK02 |
| SEEK20 | engaged, all 0 | levels | interface `LOOP-LEVELS` |
| SEEK21, 22 | 500Hz −2, +2 | ess_ladder | SEEK02 |
| SEEK23 | 125Hz +5 | levels | SEEK20 |

SEEK26 (500/1k/2k at −5) was planned and never recorded.

## Model

`models/graphic_eq/`: ten band sections (centre, Q, gain constant per band)
and one fitted slider law, in two forms: independent bands (default) and a
shared feedback network.

```python
import sys; sys.path.insert(0, "data/equipment/donner-eq-seeker/models/graphic_eq")
from model import SeekerModel
m = SeekerModel.load()
H = m.response([100, 1000], {"125": -3, "250": -3}, level=0)   # complex, vs engaged-flat
y = m.apply(x, 44100, {"500": -2, "1k": -2, "2k": -2})        # filter audio
```

RMS error over 40Hz–10kHz: 0.5dB on single-band settings, 0.9dB on
combinations in the fit, 1.7dB on combinations held out. Refit with
`python fit.py` after adding takes. `validation.json` has per-take errors,
including phase (not fitted, 1–14° RMS).

## Regenerating `measurements/`

```
python tools/export_eq_seeker.py --audio-root <folder containing reamps/SEEK*.wav>
```

The captures are listed with hashes in the repository's `audio_manifest.json`.
