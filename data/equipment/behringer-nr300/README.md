# Behringer NR300

Noise reduction pedal (Threshold, Decay), used here in its 4-cable loop: it
detects on the signal entering its send and gates its return. One unit,
daisy-chained Roland 9V supply. Measured 2026-09-15.

**Findings: [`findings.md`](findings.md).** In brief: a broadband downward
expander with a −17dB range. Its threshold runs from −70 to −24dBFS (playing
peaks at −14), most of that in the upper half of the knob. It passes −0.2dB
when open, and inverts polarity when engaged.

## Settings vocabulary

```json
{"noise_reduction": "on", "threshold": "9:00", "decay": "7:00"}
```

Knob positions are clock positions (7:00 = minimum, 5:00 = maximum, written
`min` / `max`). `noise_reduction: "off"` is the pedal's off state with the gate
held open (the knobs are then `null`).

## Takes

| take | Threshold | Decay | captures |
|---|---|---|---|
| NR01 | — (off) | — | music, levels: **the reference** |
| NR02 | 9:00 | 7:00 | music (interferer), levels |
| NR03 | min | 7:00 | music, levels |
| NR04 | 12:00 | 7:00 | music, levels |
| NR05 | 3:00 | 7:00 | music (interferer), levels |
| NR06 | max | 7:00 | music, levels |
| NR07 | 9:00 | 12:00 | music, levels |
| NR08 | 9:00 | max | music, levels |

`music` is a re-amp of a played performance of *Linkin Park – With You* (the
source project's take R03, fingerstyle, ~218s). That audio is **not published**.
Its 5ms frame envelopes are, in `measurements/envelopes.npz`, as int16 centi-dB,
with keys `<take>/<probe>/<x_rms|key_rms|key_peak|y_rms>`. `x` is the gate-off
reference aligned to that take, and `y` is the take.

## Model

`models/expander/`. A peak-detecting downward expander with hysteresis, hold
and one-pole ballistics on 5ms frames, with a parameter set for each measured
setting.

```python
import sys; sys.path.insert(0, "data/equipment/behringer-nr300/models/expander")
from model import load_params, apply_model
y = apply_model(x, load_params("NR02"), sr=44100, key=pre_loop_signal)
```

Levels are absolute: scale `x`/`key` so your played peaks sit at −14dBFS, or
set `det_offset_db` in the params. Numba speeds it up but is optional.
`python fit.py` refits everything from `envelopes.npz` (about a minute on 4
cores).

## Regenerating `measurements/`

```
python tools/export_nr300.py --audio-root <folder containing reamps/NR*.wav>
```
