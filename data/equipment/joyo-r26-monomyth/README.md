# Joyo R-26 Monomyth

Bass overdrive with a switchable drive stage, two pre-drive switches (Hi Boost,
Gain Boost), Voice, Blend, Level and a six-band EQ. One unit, daisy-chained
Roland 9V supply. Measured 2026-09-17 to 09-20.

**Findings: [`findings.md`](findings.md).** In brief: the topology is measured
end to end (switches before the clipper, Voice after it, EQ outside the drive
stage). The EQ is six symmetric filters (±10–18dB) centred on nominal. Drive
sets the amount of clipping up to 12:00 and its hardness above. With the drive
stage off the pedal is a 0.8dB-loss linear EQ.

## Settings vocabulary

`settings.control` / `settings.value` name what moved; `everything_else` says
whether Blend was left at the settled 9:00 or taken to max, and
`settled_values` lists the rest. EQ sliders are in notches, −5..+5.

## Takes

| takes | what |
|---|---|
| MYTH01 | bypassed |
| MYTH02 | engaged, drive stage OFF, EQ flat: the EQ reference |
| MYTH03–08, 35–38 | each EQ slider at +5 and −5, drive off |
| MYTH09–11 | 250Hz and 1.5kHz cuts, alone and together, drive off |
| MYTH12 | settled, drive on |
| MYTH13–15 | Blend min / 12:00 / max |
| MYTH16, 18 | Voice min / max (Blend max) |
| MYTH19–22, 23–26 | Drive min / 10:00 / 2:00 / max at Voice min, then Voice max (Blend max) |
| MYTH27–32 | Hi Boost, Gain Boost, both: at Drive 12:00 and at Drive max |
| MYTH39–42 | each switch at Drive min, and with the drive stage off |

MYTH17 is the same state as MYTH15 and was not recorded separately; MYTH33/34
(Level) were not recorded. Captures: `ess_ladder` and `levels` throughout,
sent at −23dBFS (`lad`). MYTH12/13/15 also have music (not published).

## Model

`models/asymmetric_clipper/params.json`: the fitted parameters and form,
preserved from the source project, which validated them on played
performances at 2.2–2.4dB RMS. **This repository has no runnable
implementation of it yet.** The EQ, Voice and Blend need no model: they are
linear, and their measured curves are in `measurements/`.
