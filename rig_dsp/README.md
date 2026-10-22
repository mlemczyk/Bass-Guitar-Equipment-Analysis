# rig_dsp

The analysis code behind every measurement in this dataset. numpy, scipy and
soundfile only.

| module | what it does |
|---|---|
| `stimuli.py` | Generates the test signals ("probes"): exponential-sine-sweep ladders, pink noise, two-tone, bursts, level steps, plucks, the EMG injection sweep, silence. `stimuli/generate.py` writes them, matching `stimuli/*.wav` to within 1 LSB |
| `sweep.py` | Frequency response, linearity, harmonics and noise from sweep captures, by two routes kept side by side: the legacy third-octave Welch ratios that reproduce the published findings, and Farina deconvolution (1/12 octave, with phase, per harmonic order) that the models are fitted to |
| `envelope.py` | Frame envelopes and sample alignment, for level-acting stages (gates, compressors) measured against a re-amp of real playing |
| `run.py` | Progress reporting and process-pool sizing for the scripts in `tools/` |

`methodology.md` explains why each route and convention exists, and the
mistakes that produced each rule.
