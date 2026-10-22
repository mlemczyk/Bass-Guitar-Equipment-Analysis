# Joyo R-22 Tidal Wave

Bass preamp / DI with amp-and-cab simulation. One unit, daisy-chained Roland
9V supply. Its XLR DI out feeds the mixer, so it is in the capture path even
when bypassed (bypassed, it passes the signal uncoloured). Measured 2026-09-15
and 09-16.

**Findings: [`findings.md`](findings.md).** In brief: Drive is a clean 35dB
pre-clipper gain. The cab sim is a −16dB notch at 1kHz. Presence at 12:00 is a
−18dB notch at 3.9kHz. The tone stack sits after the blend. Wide, well-centred
Treble / Middle / Bass controls (±13 to ±19dB).

## Settings vocabulary

`settings.control` / `settings.value` name the one control moved, and
`settled_values` gives every other control. Clock positions; min = 7:00,
max = 5:00. Takes "@ Blend MAX" also move Blend to max.

## Takes

| takes | what |
|---|---|
| TW01 | bypassed |
| TW02 | settled |
| TW03–06 | Drive 7:00 / 11:00 / 1:00 / max at Blend 12:00 |
| TW07–09 | Blend min / 3:00 / max |
| TW10–13 | Presence min / 9:00 / 3:00 / max |
| TW14–17 | Treble min / 9:00 / 3:00 / max |
| TW18–21 | Middle min / 3:00 / max, and max at the 1kHz switch position |
| TW22–25 | Bass min / 3:00 / max, and max at the 80Hz switch position |
| TW26, 27 | Level min / max |
| TW28 | Treble max at Blend min (where is the tone stack?) |
| TW29–32 | Drive 7:00 / 11:00 / 1:00 / max at Blend max (TW09 is 9:00) |
| TW33, 34 | superposition checks (Presence min + Treble max; a five-knob combination) |

Captures: `ess_ladder` (all), `levels` (most), and `lad30` (−30dBFS send)
repeats of several. TW02 also has music (not published), bursts, plucks and
twotone.

## Model

`models/wiener_hammerstein/`: `model.py`, `params.json`, `responses.npz` (the
complex H2 and dry-leg responses), `validate.py`.

```python
import sys; sys.path.insert(0, "data/equipment/joyo-r22-tidal-wave/models/wiener_hammerstein")
from model import TidalWave
y = TidalWave.load().apply(x, drive="11:00", blend="12:00")   # x at send scale (playing peak ~ -23dBFS)
```
