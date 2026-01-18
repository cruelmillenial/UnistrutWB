"""
Load layer (Canonical -> JSON artifacts, optional SQLite).

Primary output:
- unistrut.json (git-friendly)
- mapping_hole_series.json
- notes_derating.json

Optional:
- SQLite mirror (not implemented in this starter).
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def write_json(path: Path, obj: object) -> str:
    payload = json.dumps(obj, indent=2, sort_keys=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return _sha256_bytes(payload)

def load(ds: dict, out_dir: str) -> dict:
    out = Path(out_dir)

    # rules file is intentionally separate (for query-time application)
    mapping_hole_series = {
        "schema_version": ds["meta"].get("schema_version","0.1.0"),
        "hole_series": {
            "T": {"kind": "slots", "beam_capacity_factor": 0.85},
            "SL": {"kind": "holes_or_slots", "beam_capacity_factor": 0.90},
            "HS": {"kind": "slots", "beam_capacity_factor": 0.90},
            "KO": {"kind": "knockouts", "beam_capacity_factor": 0.95},
        },
        "provenance": {"source_pages": [], "notes": ["Populate pitch/slot geometry when extracted."]},
    }

    notes_derating = {
        "schema_version": ds["meta"].get("schema_version","0.1.0"),
        "notes": [
            {"id":"bolt_torque_note","text":"Design bolt torque values depend on thread condition; lubrication can increase bolt tension.","provenance":{"source_pages":[],"anchor":"DESIGN BOLT TORQUE"}},
            {"id":"units_note","text":"Imperial dimensions are illustrated in inches; metric in parentheses; unless noted, metric is mm rounded to one decimal place.","provenance":{"source_pages":[],"anchor":"DIMENSIONS"}},
        ],
    }

    sha_unistrut = write_json(out / "unistrut.json", ds)
    sha_mapping = write_json(out / "mapping_hole_series.json", mapping_hole_series)
    sha_notes = write_json(out / "notes_derating.json", notes_derating)

    return {"unistrut.json": sha_unistrut, "mapping_hole_series.json": sha_mapping, "notes_derating.json": sha_notes}
