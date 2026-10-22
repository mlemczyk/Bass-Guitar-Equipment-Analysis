# tools

Scripts that turn audio captures into this repository's measurement files, and
rebuild the index. The captures themselves are not in the repo
(`audio_manifest.json` lists them), so the export scripts need a folder that
holds them, passed as `--audio-root`.

| script | what it writes |
|---|---|
| `export_pedal.py <pedal>\|all` | every capture of one pedal (Tidal Wave, Monomyth, Big Muff, BC-1X) to `data/equipment/<pedal>/measurements/`, using the take table in `takes/<pedal>.json` |
| `export_eq_seeker.py` | the Donner EQ Seeker's 28 takes |
| `export_nr300.py` | the Behringer NR300's takes, and the frame envelopes its model is fitted to |
| `export_emg.py` | the EMG BQC injection sweeps, and the Y-split cable check (to `interface/`) |
| `export_interface.py` | the re-amp loop's own round trip, noise floor and level steps (to `interface/`) |
| `build_index.py` | `index.json` and `audio_manifest.json`, from the files on disk |

```bash
python tools/export_pedal.py joyo-r22-tidal-wave --audio-root "<folder holding reamps/>"
python tools/build_index.py
```

Run `build_index.py` after adding or changing any measurement. Every ratio is
taken against a reference capture from the same session (see
`export_pedal.py`'s REFERENCE RULE and `methodology.md`), and captures are
analysed in parallel, with progress and pool sizing from `rig_dsp/run.py`.
Never hand-edit a measurement JSON: change the script and re-export.
