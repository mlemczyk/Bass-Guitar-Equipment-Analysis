#!/usr/bin/env python3
"""Rebuild index.json and audio_manifest.json from the files on disk.

    python tools/build_index.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def main():
    index = {"schema": "rig-equipment/index@1", "equipment": {}, "interface": []}
    audio = {}

    def note_capture(cap, used_by):
        e = audio.setdefault(cap["file"], {"sha256": cap.get("sha256"),
                                           "sample_rate": cap.get("sample_rate"),
                                           "probe": cap.get("probe"),
                                           # a re-amp of a played song: never published
                                           "publishable": cap.get("probe") != "music",
                                           "used_by": []})
        if used_by not in e["used_by"]:
            e["used_by"].append(used_by)

    for d in sorted((REPO / "data" / "equipment").iterdir()):
        if not d.is_dir():
            continue
        takes, datasets = [], []
        for p in sorted((d / "measurements").glob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            if doc.get("schema") != "rig-equipment/take@1":
                datasets.append({"path": p.relative_to(REPO).as_posix(), "schema": doc.get("schema"),
                                 "description": doc.get("description")})
                continue
            caps = []
            for c in doc.get("captures", []):
                cap = c["capture"]
                note_capture(cap, f"{d.name}/{doc['take_id']}")
                caps.append({"file": cap["file"], "probe": cap["probe"],
                             "recorded": cap.get("recorded"),
                             "superseded": bool(cap.get("superseded")),
                             "reference": (c.get("reference") or {}).get("take_id")})
            takes.append({"take_id": doc["take_id"], "description": doc.get("description"),
                          "settings": doc.get("settings"), "path": p.relative_to(REPO).as_posix(),
                          "captures": caps})
        models = []
        for m in sorted((d / "models").glob("*/params.json")):
            v = m.with_name("validation.json")
            models.append({"name": m.parent.name, "path": m.parent.relative_to(REPO).as_posix(),
                           "has_validation": v.exists()})
        index["equipment"][d.name] = {
            "readme": (d / "README.md").relative_to(REPO).as_posix(),
            "findings": (d / "findings.md").relative_to(REPO).as_posix()
            if (d / "findings.md").exists() else None,
            "n_takes": len(takes), "takes": takes, "datasets": datasets,
            "envelopes": (d / "measurements" / "envelopes.npz").relative_to(REPO).as_posix()
            if (d / "measurements" / "envelopes.npz").exists() else None,
            "models": models}

    for p in sorted((REPO / "interface" / "measurements").glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("capture", {}).get("sha256"):
            note_capture(doc["capture"], f"interface/{doc['take_id']}")
        index["interface"].append({"take_id": doc["take_id"], "description": doc.get("description"),
                                   "path": p.relative_to(REPO).as_posix()})

    manifest = {"schema": "rig-equipment/audio-manifest@1",
                "note": ("Captures are not stored in git. Paths are relative to the audio "
                         "root that the tools/ scripts take as --audio-root."),
                "hosted_at": None,
                "files": dict(sorted(audio.items()))}
    (REPO / "index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    (REPO / "audio_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"index: {len(index['equipment'])} equipment folders, "
          f"{sum(e['n_takes'] for e in index['equipment'].values())} takes; "
          f"manifest: {len(audio)} captures")


if __name__ == "__main__":
    main()
