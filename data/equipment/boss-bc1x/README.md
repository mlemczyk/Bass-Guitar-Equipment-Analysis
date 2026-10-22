# Boss BC-1X

Bass compressor: Threshold, Ratio, Release, Level. One unit, daisy-chained
Roland 9V supply. Measured 2026-09-16 to 09-29.

**Findings: [`findings.md`](findings.md).** In brief: a two-band compressor
split near 310Hz, the same ~2.8:1 ratio in both bands, and the high band
starting 10dB lower. +7.7dB makeup. Compression is program-dependent (plucks
are compressed 2–2.5dB more than steady tones). Threshold does all its work
between min and about 1:00.

## Settings vocabulary

Each take's `settings` gives the one `control` moved and its `value`; every
other knob is at `settled_values` (Threshold 12:00, Ratio 12:00, Release 12:00,
Level 11:00). Clock positions; min = 7:00, max = 5:00.

## Takes

| take | setting | captures |
|---|---|---|
| BC01 | settled | ess_ladder, levels, music, bursts, plucks, twotone |
| BC02–05 | Threshold min, 9:00, 3:00, max | music, plucks |
| BC06, BC08 | Ratio min, max | music, plucks |
| BC07 | Ratio 3:00 | ess_ladder |
| BC09–11 | Release min, 3:00, max | music, plucks, bursts |
| BC15 | **bypassed** | ess_ladder, music, bursts, plucks |

BC12–14 (Level) were never recorded. `music` is a re-amp of a played song (not
published). `envelopes.npz` has the 5ms frame envelopes of every music,
bursts and plucks capture and its aligned bypass reference, under
`<take>/<probe>_lad/<x_rms|y_rms|key_peak>`.

## Model

`models/twoband/`: `model.py` (numpy/scipy, numba optional), `params.json`,
`validate.py` (needs the captures), `validation.json`.

```python
import sys; sys.path.insert(0, "data/equipment/boss-bc1x/models/twoband")
from model import load_params, apply_model
y = apply_model(x, load_params(), sr=44100)   # x scaled so playing peaks at about -14dBFS
```
