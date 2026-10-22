# EHX Deluxe Bass Big Muff Pi

Fuzz: Sustain, Tone, Blend, Volume, Gate, and a crossover (HPF on the fuzz path,
LPF on the clean path, switchable). One unit, daisy-chained Roland 9V supply.
Measured 2026-09-16 to 09-20.

**Findings: [`findings.md`](findings.md).** In brief: symmetric clipping (odd
harmonics 13–47dB over even). Sustain saturates by 3:00. Tone is mostly a bass
cut, with its authority in the upper half of the knob. The crossover is a
resonant 2nd-order filter pair. Blend changes dynamics as well as mix.

## Settings vocabulary

`settings.control` / `settings.value` name what moved; `everything_else` says
whether Blend was taken to max. `settled_values` lists the rest. Clock
positions; Tone 5:00 = max.

## Takes

| takes | what |
|---|---|
| MUFF01 | bypassed |
| MUFF02 | settled |
| MUFF03–06, 26–29 | Tone × Sustain corners at Blend 12:00, and at Blend max |
| MUFF07–10, 16 | Sustain min / 9:00 / 3:00 / max, and 12:00, at Blend max |
| MUFF11–13 | Tone min / 9:00 / 12:00 at Blend max |
| MUFF14, 16, 36, 37 | Blend min / max / 9:00 / 3:00 |
| MUFF17, 18 | Gate min / max |
| MUFF19, 30, 31 | crossover engaged at settled corners: Blend 12:00 / min / max |
| MUFF32–35 | HPF min / max (Blend max), LPF min / max (Blend min) |

MUFF15 = MUFF02 and was not recorded; MUFF20–25 were never recorded. Captures:
`ess_ladder` and `levels`; MUFF02/11/16/19 also music (not published).

## Model

`models/circuit/`: `muff_circuit.py` (the circuit solver: numpy + **numba
required**), `model.py` (fitted wrapper with Blend), `params.json`,
`validate.py`, `validation.json`.

```python
import sys; sys.path.insert(0, "data/equipment/ehx-deluxe-bass-big-muff/models/circuit")
from model import BigMuff
y = BigMuff.load().apply(x, 44100, sustain="2:00", tone="12:00", blend="max")
```

About 0.25s per second of audio after a ~2s first-call compile.
