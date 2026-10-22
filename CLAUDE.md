# Bass rig equipment data: a guide for AI agents

Measurements, fitted models and findings for the bass-guitar equipment of one
real rig: a Yamaha TRBX305 with an EMG preamp, a pedalboard of eight units
(six of them measured here; the tuner and volume pedal are not), and an Allen &
Heath ZEDi-10 interface. Use it as a **benchmark**. If you own the same pedal,
compare your measurements against these. If you are modelling one, start from
these parameters, and check your model against the per-take curves.

Released into the public domain (the Unlicense, `LICENSE`). No attribution is required.

## Read in this order

1. **This file.**
2. `index.json`: everything that is here, machine-readable (equipment →
   takes → captures, models).
3. `data/equipment/<pedal>/README.md`, then that pedal's `findings.md`.
4. `methodology.md`, before comparing numbers, and `schema.md` for the
   JSON fields.
5. `interface/README.md` if a result looks like compression or drift.
6. `rig.md` for the instrument and the signal chain.

## Layout

| path | what |
|---|---|
| `data/equipment/<pedal>/measurements/` | one JSON per take: the setting, and its frequency response, linearity, harmonics and noise |
| `data/equipment/<pedal>/models/<name>/` | `model.py` (numpy/scipy, plus numba for the Big Muff circuit; see `requirements.txt`), `params.json`, `fit.py` (refits from `measurements/`), `validation.json` |
| `data/equipment/<pedal>/findings.md` | what the measurements show, citing take IDs |
| `interface/` | the re-amp loop itself: round trip, noise floor, where it distorts, session drift |
| `stimuli/` | the probe WAVs and `generate.py`, which rebuilds them to within 1 LSB |
| `rig_dsp/` | the analysis code |
| `tools/` | scripts that turn audio captures into `measurements/` |

### Equipment status

| folder | takes | model | model status |
|---|---|---|---|
| `donner-eq-seeker` | 28 | `graphic_eq`: 10 band sections + fitted slider law | fitted here, cross-validated |
| `behringer-nr300` | 8 + envelopes | `expander`: gate with hysteresis/hold/ballistics | refitted here from published envelopes |
| `boss-bc1x` | 12 + envelopes | `twoband`: split compressor, hybrid detector | ported, reproduces source to 0.001dB |
| `joyo-r22-tidal-wave` | 34 | `wiener_hammerstein`: gain → clipper → complex filter, + Blend | ported, re-validated here |
| `joyo-r26-monomyth` | 39 | `asymmetric_clipper` | **parameters only**, not runnable here |
| `ehx-deluxe-bass-big-muff` | 30 | `circuit`: Black Russian core, DK-method solver | ported, re-validated here |
| `emg-bqc` | 23 | none (linear; the curves are the model) | — |
| `instrument-trbx305` | string decay dataset | none | — |

**The most important caveat in this dataset** is the re-amp loop's own
headroom (`interface/README.md`). Several source-project conclusions about
boosts compressing were the loop, and each pedal's findings say which.

## Things to know before using a number

- **Every response is a ratio against a same-session reference capture**,
  given in each capture's `reference` block. The loop divides out. Absolute
  levels (`*_dbfs`) do not, and are specific to this interface's gain.
- **Use the small-signal rungs.** Ladder rungs 0–2 (sent at −70/−60/−50dBFS)
  are the pedal. Check `return_peak_dbfs` on rungs 3–4: above about −21dBFS
  the loop's own distortion begins, and it was once mistaken for the pedal's
  (`interface/README.md`).
- **`legacy_*` fields reproduce the original published numbers**
  (third-octave Welch, magnitude only). **`farina_*` fields** are finer,
  1/12-octave, with phase. Models are fitted to Farina.
- Fields marked `superseded` are kept on purpose, as evidence of a mistake
  documented in that pedal's `findings.md`. Don't use them as data.
- **Audio is not in git.** `audio_manifest.json` lists each capture by
  path and sha256, with `publishable: false` on re-amps of played songs.
  For level-acting stages (gates, compressors) measured on those, the 5ms
  frame envelopes are published instead (`measurements/envelopes.npz`), and
  are enough to refit the models. Captures of copyrighted song performances (the source
  project's played takes, e.g. *Linkin Park – With You* used as a re-amp
  source) are never published. Numbers derived from them are.

## Adding data (agents and humans)

- New takes go in `data/equipment/<pedal>/measurements/` in the existing
  schema, produced by a script in `tools/` that reads WAV captures. Never
  hand-edit measurement JSON.
- Record each capture with `ess_ladder` against a same-session reference. Keep
  the return below −21dBFS peak, and say which reference you used.
- A new pedal gets the same layout: `README.md` (unit, settings vocabulary,
  how measured), `findings.md` (claims, each citing take IDs), `measurements/`,
  and `models/` when there is a fit. Add it to the table above, then run
  `python tools/build_index.py`.
- When a finding is overturned, keep the old claim under "Superseded" in
  `findings.md` with the reason. Don't delete it.
- Scripts here report progress with `rig_dsp.run.Progress`, and size process
  pools with `rig_dsp.run.workers`. Keep both in new scripts.

## Provenance

Measured 2026-09-13 to 2026-10-18 by the owner of the rig. "The source project"
in these files means the private measurement workspace the data came from.
Only equipment measurements, models and methods are published here.
