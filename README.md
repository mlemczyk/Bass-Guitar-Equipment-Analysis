# Bass Guitar Equipment Analysis

By Michal Lemczyk.

Measured frequency responses, linearity, harmonics and noise, and fitted
models, for the equipment of one real bass rig: six pedals, the bass's onboard
EMG preamp, the instrument itself, and the audio interface loop they were
measured through. Every number comes from re-amping test signals through the
real hardware. It is written to be used as benchmark data, by people and by AI
agents: if you own the same pedal, compare your measurements with these; if
you are modelling one, start from these parameters and check your model
against the per-take curves.

| equipment | data |
|---|---|
| [Donner EQ Seeker](data/equipment/donner-eq-seeker/) — 10-band graphic EQ | 28 takes, fitted model, findings |
| [Behringer NR300](data/equipment/behringer-nr300/) — noise gate | 8 takes, frame envelopes, fitted model |
| [Boss BC-1X](data/equipment/boss-bc1x/) — bass compressor | 12 takes, two-band model |
| [Joyo R-22 Tidal Wave](data/equipment/joyo-r22-tidal-wave/) — preamp/DI | 34 takes, drive model |
| [Joyo R-26 Monomyth](data/equipment/joyo-r26-monomyth/) — bass overdrive | 39 takes, measured topology, clipper parameters |
| [EHX Deluxe Bass Big Muff](data/equipment/ehx-deluxe-bass-big-muff/) — fuzz | 30 takes, circuit model |
| [EMG BQC](data/equipment/emg-bqc/) — onboard preamp | 23 injection sweeps |
| [Yamaha TRBX305](data/equipment/instrument-trbx305/) — the bass | string decay dataset, findings |
| [The re-amp loop](interface/) | round trip, noise, headroom, drift, Y-split |

**AI agents: start with [`CLAUDE.md`](CLAUDE.md)**, which gives the reading
order, the layout and the caveats to know before using a number.

## How it was measured

- **Re-amping.** A test signal is played out of the computer, through the
  pedal and back in. The signal is byte-identical on every pass, so dividing
  a capture by a reference capture from the same session cancels the content
  and leaves only the pedal. Same-session reproducibility is 0.01 dB.
- **Exponential-sine-sweep ladders** at five send levels, 10 dB apart, give
  the response at each level, so linearity is measured rather than assumed,
  plus the harmonic orders and the noise floor.
- **Two analysis routes, kept side by side:** the original third-octave Welch
  ratios, and Farina deconvolution at 1/12 octave with phase, which the models
  are fitted to.
- **The loop itself is characterised** (`interface/`): its round trip, noise,
  drift between sessions, and the level at which it starts to distort. That
  last one matters, because loop distortion was once mistaken for a pedal's.
- **Models are fitted to the measurements and checked against them**, each
  with its own `validation.json`: a graphic EQ with a fitted slider law
  (cross-validated), a gate with hysteresis and hold, a split-band
  compressor, a Wiener–Hammerstein drive model, and a circuit-level Big Muff
  model solved with the DK method. The Monomyth has measured clipper
  parameters but no runnable model yet.

[`methodology.md`](methodology.md) has the full method, and the mistakes that
taught each rule.

## The pedals

The measured units themselves. The knob positions in these photos are
incidental: each take's setting is in its `measurements/` JSON.

| | | |
|:---:|:---:|:---:|
| <img src="images/joyo-r22-tidal-wave.jpg" width="300" alt="Joyo R-22 Tidal Wave"><br>Joyo R-22 Tidal Wave | <img src="images/ehx-deluxe-bass-big-muff.jpg" width="300" alt="EHX Deluxe Bass Big Muff Pi"><br>EHX Deluxe Bass Big Muff | <img src="images/joyo-r26-monomyth.jpg" width="300" alt="Joyo R-26 Monomyth"><br>Joyo R-26 Monomyth |
| <img src="images/boss-bc1x.jpg" width="160" alt="Boss BC-1X Bass Comp"><br>Boss BC-1X | <img src="images/behringer-nr300.jpg" width="160" alt="Behringer NR300 Noise Reducer"><br>Behringer NR300 | |

## Using the data

- Measurements are JSON (`schema.md` describes the fields), indexed in
  [`index.json`](index.json).
- The analysis code (`rig_dsp/`, `tools/`, and each model's `model.py` and
  `fit.py`) needs Python 3.10+ and [`requirements.txt`](requirements.txt):
  numpy, scipy, soundfile and numba.
- **The audio captures are not in this repo.**
  [`audio_manifest.json`](audio_manifest.json) lists every capture by path and
  SHA-256, and marks which could be published. They have not been published
  yet. Re-amps of played songs never will be; the numbers derived from them
  are here.

## How this was built

The rig is mine. I recorded every capture on it, over five weeks in
September and October 2026, and directed the analysis: what to measure and
what counted as proof. The analysis code,
models and documentation were developed with
[Claude Code](https://claude.com/claude-code), Anthropic's AI coding agent,
in a private measurement workspace, and moved into this repo for publication.
Commits it helped write carry a `Co-Authored-By: Claude` line, and
[`CLAUDE.md`](CLAUDE.md) is written for agents that use or extend the data.

## Related projects

Part of one personal project: recording bass covers along to Guitar Pro tabs,
scoring them, and matching my rig's tone to the original recordings.

- [Recording Footswitch](https://github.com/mlemczyk/footswitch): the
  four-button USB footswitch that starts, stops and discards takes hands-free.
- [Guitar Pro Utilities](https://github.com/mlemczyk/Guitar-Pro-Utilities):
  Python tools for the tabs: parsing, syncing backing tracks, embedding audio,
  MIDI export and difficulty.

## License

Public domain, under the [Unlicense](LICENSE).
