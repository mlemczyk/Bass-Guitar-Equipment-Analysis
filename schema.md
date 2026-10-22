# Schema

Every JSON file carries a `schema` field. Values are rounded: dB to 0.01,
phase to 0.1°, Hz to 0.01. `null` means not measured or masked (below the
noise floor).

## `rig-equipment/take@1`: `data/equipment/<pedal>/measurements/<TAKE>.json`

One file per take: one physical setting of one pedal, with one or more captures.

| field | meaning |
|---|---|
| `equipment` | folder name of the pedal |
| `take_id` | stable ID; cited by `findings.md` |
| `description` | the setting, in words |
| `settings` | the setting, machine-readable. Pedal-specific; see that pedal's `README.md` |
| `captures[]` | one entry per probe recorded at this setting |

### A sweep capture (`capture.probe` = `ess_ladder` or `ess`)

| field | meaning |
|---|---|
| `capture.file` | path of the WAV, relative to the audio root (see `audio_manifest.json`) |
| `capture.sha256` | hash of that WAV |
| `capture.recorded` | date the capture was written (file time, local) |
| `capture.superseded` | non-null when a better capture of the same take exists |
| `reference` | the capture this one is divided by: `take_id`, `file`, `sha256` |
| `farina_grid_hz` | 1/12-octave grid, 20Hz–20kHz (121 points), shared by every `farina_*` array |
| `harmonic_fundamentals_hz` | third-octave grid, 31.5Hz–1.6kHz, for `harmonics_*` |
| `rungs[]` | one per sweep: five for `ess_ladder` (quietest first), one for `ess` |
| `noise`, `reference_noise` | the capture's tail after the last sweep: `rms_dbfs_20_20k`, `third_octave_dbfs` [[Hz, dBFS per band]] |

Each rung:

| field | meaning |
|---|---|
| `rung` | 0 = quietest |
| `file_level_dbfs` | level of this sweep inside the probe file |
| `send_peak_dbfs` | peak level as it left the computer (null if not documented) |
| `return_peak_dbfs` | peak of this sweep as captured. **Above −21, the loop's own distortion begins** |
| `reference_return_peak_dbfs` | same, for the reference capture |
| `farina_db`, `farina_phase_deg` | take ÷ reference, complex, Farina route, on `farina_grid_hz` |
| `legacy_third_octave_db` | [[centre Hz, dB]], take ÷ reference, Welch route |
| `legacy_usable_pct_40_10k` | share of 40Hz–10kHz bins above both noise floors |
| `harmonics_db_rel_fundamental` | `{h2..h5: [dB at each harmonic_fundamentals_hz]}`, **absolute** for this capture (loop included), not a ratio |

### A level-steps capture (`capture.probe` = `levels`)

`steps[]`, one per 110Hz step (eight, quietest first): `file_level_dbfs`,
`fundamental_dbfs_peak` (as captured), `harmonics_db_rel_fundamental`
{h2..h5}, `thd_pct_h2_h5`. Absolute, not a ratio. Compare against
`interface/measurements/LOOP-LEVELS.json` for the loop's own share.

### A gate capture (`capture.probe` = `music` or `levels`, level-acting stages)

| field | meaning |
|---|---|
| `capture.contaminated` | non-null when the capture carries something that is not the pedal |
| `alignment` | `lag_samples` against the reference, `polarity_vs_reference` |
| `peak_dbfs` | `positive`, `negative`: largest excursion each way |
| `frame_percentiles` (music) | `reference_dbfs` and `change_db` at percentiles 1/10/25/50/75/95 of 5ms frame RMS |
| `frame_gain_db_by_class` (music) | output−input per frame, `median` and `p10`, for `music` (input > −60dBFS), `transition` (−85 to −60) and `rest` (≤ −85) |
| `musical_frames_band_gain` (music) | per octave on music frames: `power_db` (Pyy/Pxx), `coherent_db` (\|Pxy\|/Pxx), `coherence` |
| `steps` (levels) | per 110Hz step: `input_frame_rms_dbfs`, `gain_db` |

`measurements/envelopes.npz` holds the frame envelopes behind these, as int16
centi-dB, under keys `<take>/<music|levels>/<x_rms|key_rms|key_peak|y_rms>`.

### Other capture kinds in pedal folders

- `bursts`, `plucks`: `peak_dbfs`, `alignment`, and an `envelope` pointer
  into `envelopes.npz` (`<take>/<probe>_<tag>/<x_rms|y_rms>`, take and
  aligned bypass reference).
- `twotone`: `steps[]` with `low_80hz_dbfs` and `probe_<Hz>hz_dbfs` for each
  step of the 80Hz tone.
- Pedal takes (BC-1X, Tidal Wave, Monomyth, Big Muff) carry `settings` as
  `{control, value, everything_else, settled_values}` text, from the source
  project's recording matrix, and the `reference` block adds `state` and
  `days_apart`.

### EMG injection takes (`emg-bqc`)

`captures[0].curve_db` [[Hz, dB]] against H00 on a linear ~37Hz grid,
`summary` {extreme_db, extreme_hz, corner_hz, shape, db_at_*}, and
`session_drift_db` (H99 vs H00 for that region).

## `rig-equipment/partial-decay@1`

`instrument-trbx305/measurements/string_decay.json`: `rows[]` of per-partial
decay fits. Columns are documented inside the file.

## `rig-equipment/loop@1`: `interface/measurements/*.json`

As above, for measurements of the re-amp loop itself. `LOOP-NULL` is
divided by the digital probe rather than by a capture.

## `rig-equipment/model-params@1`: `data/equipment/<pedal>/models/<model>/params.json`

Fitted parameters, read by the `model.py` beside it. Fields are documented
in that `model.py`'s docstring. `validation.json` beside it holds the
model's errors per take: in-sample, and left-out where cross-validated.

## `index.json`, `audio_manifest.json` (repo root)

Generated by `tools/build_index.py`. `index.json` lists each equipment
folder with its takes (ID, description, probes) and models. `audio_manifest.json`
maps each capture path to its sha256, sample rate and the take that uses it.
