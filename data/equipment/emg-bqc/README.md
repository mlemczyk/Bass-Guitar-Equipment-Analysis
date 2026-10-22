# EMG BQC (HZ) onboard preamp

Active 3-band preamp with sweepable mid, pickup pan and two treble DIP switches,
fitted to a Yamaha TRBX305 with its stock passive M3 pickups. 18V from two 9V
LiPo batteries. Measured 2026-09-13 by magnetic injection into the pickups
(23 sweeps).

**Findings: [`findings.md`](findings.md).** In brief: the Bass shelf corner is
~200Hz (not 50Hz). The Treble shelf starts ~2.3kHz (not 300Hz). Mid is a
Q≈1 peaking filter from 112Hz to ~1.05kHz. Every control does ~2dB over its
inner ±2 notches and ~12–15dB at ±5.

## Settings vocabulary

```json
{"bass": 0, "mid": 5, "midfreq": -5, "treble": 0, "pickup_pan": 0, "treble_dip_sw1_sw2": "OFF/OFF"}
```

Notches from centre, −5..+5. `pickup_pan` +5 = full neck, −5 = full bridge.

## Files

`measurements/H01.json`–`H22.json`, `H99.json`: each holds `curve_db` [[Hz,
dB]] against H00 (linear frequency spacing, ~37Hz steps), a `summary`
(extreme, corner, shape, values at 50/250/1k/3k/10kHz), and `session_drift_db`.
The raw injection sweeps (`raw_takes/H*.wav`) are listed in
`audio_manifest.json`. `tools/export_emg.py` rebuilds these files from the
source project's `emg_sweep.py` output; that script is not ported yet.

No model is published. Every control is linear at injection level, so the
curves are the model. Interpolate between notches only for MidFreq.
