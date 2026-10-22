#!/usr/bin/env python3
"""Regenerate the probe WAVs from rig_dsp.stimuli and check them against the
committed files.

    python stimuli/generate.py            # compare only
    python stimuli/generate.py --write    # overwrite stimuli/*.wav

`emg_sweep.wav` is not generated here; see stimuli/README.md.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from rig_dsp import stimuli as st  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    for name, data, desc in st.all_probes():
        path = HERE / name
        if args.write:
            sf.write(path, data, st.SAMPLE_RATE, subtype="PCM_24")
            print(f"wrote {name:18s} {desc}")
            continue
        if not path.exists():
            print(f"{name:18s} MISSING")
            continue
        disk, sr = sf.read(path, dtype="float64")
        # round-trip the regenerated signal through PCM_24 quantisation
        q = np.round(np.asarray(data, dtype=np.float64) * 2 ** 23) / 2 ** 23
        same = sr == st.SAMPLE_RATE and len(disk) == len(q)
        diff = float(np.max(np.abs(disk - q))) if same else float("nan")
        print(f"{name:18s} {'MATCH' if same and diff <= 2 ** -23 else 'DIFFERS'}"
              f"  max |diff| {diff:.2e}  {desc}")


if __name__ == "__main__":
    main()
