#!/usr/bin/env python3
"""
Smoke-test fittings.json schema health.

Run from repo root:

    python3 tests/smoke_fittings_schema.py

No FreeCAD dependency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FITTINGS_JSON = REPO_ROOT / "Mod" / "UnistrutWB" / "data" / "fittings.json"


REQUIRED_FITTING_FIELDS = [
    "id",
    "name",
    "category",
    "display_group",
    "variant_label",
    "family_id",
    "geometry_type",
    "hole_diameter_options_in",
    "default_hole_diameter_in",
    "hardware_preset",
    "placement",
    "anchor",
    "orientation",
    "mate_frames",
]

REQUIRED_PLACEMENT_FIELDS = [
    "supported_modes",
    "allowed_face_classes",
    "slot_policy",
]

REQUIRED_MATE_FRAME_FIELDS = [
    "id",
    "kind",
    "role",
]


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def load_fittings(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise TypeError(f"{path}: expected top-level JSON object")

    fittings = raw.get("fittings")
    if not isinstance(fittings, list):
        raise TypeError(f"{path}: expected top-level 'fittings' list")

    return fittings


def validate_fitting(fitting: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []

    fid = fitting.get("id") or f"<missing id at index {index}>"

    for field in REQUIRED_FITTING_FIELDS:
        if field not in fitting:
            fail(errors, f"{fid}: missing required field '{field}'")
        elif is_missing(fitting.get(field)):
            fail(errors, f"{fid}: required field '{field}' is empty")

    placement = fitting.get("placement")
    if isinstance(placement, dict):
        for field in REQUIRED_PLACEMENT_FIELDS:
            if field not in placement:
                fail(errors, f"{fid}: placement missing required field '{field}'")
            elif is_missing(placement.get(field)):
                fail(errors, f"{fid}: placement field '{field}' is empty")
    elif "placement" in fitting:
        fail(errors, f"{fid}: placement must be an object")

    mate_frames = fitting.get("mate_frames")
    if isinstance(mate_frames, list):
        for i, frame in enumerate(mate_frames):
            if not isinstance(frame, dict):
                fail(errors, f"{fid}: mate_frames[{i}] must be an object")
                continue

            frame_id = frame.get("id") or f"<missing frame id at index {i}>"

            for field in REQUIRED_MATE_FRAME_FIELDS:
                if field not in frame:
                    fail(errors, f"{fid}: mate frame {frame_id} missing required field '{field}'")
                elif is_missing(frame.get(field)):
                    fail(errors, f"{fid}: mate frame {frame_id} field '{field}' is empty")
    elif "mate_frames" in fitting:
        fail(errors, f"{fid}: mate_frames must be a list")

    hole_options = fitting.get("hole_diameter_options_in")
    default_hole = fitting.get("default_hole_diameter_in")

    if isinstance(hole_options, list) and hole_options:
        try:
            hole_options_float = [float(x) for x in hole_options]
            default_hole_float = float(default_hole)
            if default_hole_float not in hole_options_float:
                fail(
                    errors,
                    f"{fid}: default_hole_diameter_in={default_hole} "
                    f"is not listed in hole_diameter_options_in={hole_options}",
                )
        except (TypeError, ValueError):
            fail(errors, f"{fid}: hole diameter values must be numeric")

    geometry_type = fitting.get("geometry_type")
    legacy_type = fitting.get("type")

    if geometry_type and legacy_type and geometry_type != legacy_type:
        fail(
            errors,
            f"{fid}: geometry_type='{geometry_type}' differs from legacy type='{legacy_type}'",
        )

    return errors


def main() -> int:
    if not FITTINGS_JSON.exists():
        print(f"ERROR: missing file: {FITTINGS_JSON}", file=sys.stderr)
        return 2

    try:
        fittings = load_fittings(FITTINGS_JSON)
    except Exception as e:
        print(f"ERROR: failed to load {FITTINGS_JSON}: {e}", file=sys.stderr)
        return 2

    errors: list[str] = []

    seen_ids: set[str] = set()

    for index, fitting in enumerate(fittings):
        if not isinstance(fitting, dict):
            errors.append(f"fittings[{index}]: record must be an object")
            continue

        fid = fitting.get("id")
        if fid:
            if fid in seen_ids:
                errors.append(f"{fid}: duplicate fitting id")
            seen_ids.add(fid)

        errors.extend(validate_fitting(fitting, index))

    if errors:
        print("fittings.json schema smoke test FAILED")
        print()
        for err in errors:
            print(f"- {err}")
        return 1

    print("fittings.json schema smoke test passed")
    print(f"validated {len(fittings)} fitting record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())