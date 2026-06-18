#!/usr/bin/env python3
"""
Smoke-test profiles.json schema health.

Run from repo root:

    python3 scripts/smoke_profiles_schema.py

No FreeCAD dependency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILES_JSON = REPO_ROOT / "Mod" / "UnistrutWB" / "data" / "profiles.json"
MAPPING_HOLE_SERIES_JSON = REPO_ROOT / "Mod" / "UnistrutWB" / "data" / "mapping_hole_series.json"


REQUIRED_PROFILE_FIELDS = [
    "id",
    "family",
    "gauge",
    "geometry",
    "finishes",
    "standard_lengths",
]

REQUIRED_GEOMETRY_FIELDS = [
    "width",
    "height",
    "thickness",
]

REQUIRED_MM_VALUE_FIELDS = [
    "width",
    "height",
    "thickness",
]

REQUIRED_LIPPED_PROFILE_SPEC_FIELDS = [
    "kind",
    "t",
    "lip_return",
]


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def get_nested(obj: dict[str, Any], path: list[str]) -> Any:
    cur: Any = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def has_numeric_mm(obj: dict[str, Any], field: str) -> bool:
    val = get_nested(obj, [field, "mm"])
    if val is None:
        return False

    try:
        float(val)
    except (TypeError, ValueError):
        return False

    return True


def load_profiles(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise TypeError(f"{path}: expected top-level JSON object")

    profiles = raw.get("profiles")
    if not isinstance(profiles, list):
        raise TypeError(f"{path}: expected top-level 'profiles' list")

    return profiles


def load_hole_series(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise TypeError(f"{path}: expected top-level JSON object")

    hole_series = raw.get("hole_series")
    if isinstance(hole_series, dict):
        return hole_series

    series = raw.get("series")
    if isinstance(series, dict):
        return series

    raise TypeError(f"{path}: expected top-level 'hole_series' object")


def validate_piercing_series(
    profile: dict[str, Any],
    index: int,
    hole_series: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    pid = profile.get("id") or f"<missing id at index {index}>"

    geometry = profile.get("geometry")
    if not isinstance(geometry, dict):
        return errors

    piercing = geometry.get("piercing")
    if piercing in (None, {}):
        return errors

    if not isinstance(piercing, dict):
        fail(errors, f"{pid}: geometry.piercing must be an object when present")
        return errors

    series_id = piercing.get("series")
    if series_id in (None, ""):
        return errors

    if not isinstance(series_id, str):
        fail(errors, f"{pid}: geometry.piercing.series must be a string or null")
        return errors

    if series_id not in hole_series:
        fail(errors, f"{pid}: geometry.piercing.series '{series_id}' not found in mapping_hole_series.json")
        return errors

    series_record = hole_series[series_id]
    if not isinstance(series_record, dict):
        fail(errors, f"{pid}: hole series '{series_id}' mapping must be an object")
        return errors

    slot_pattern = series_record.get("slot_pattern")
    if not isinstance(slot_pattern, dict):
        fail(errors, f"{pid}: hole series '{series_id}' missing usable slot_pattern object")
        return errors

    for field_name in (
        "pitch_mm",
        "slot_length_mm",
        "slot_width_mm",
    ):
        value = slot_pattern.get(field_name)
        try:
            if float(value) <= 0:
                fail(errors, f"{pid}: hole series '{series_id}' slot_pattern.{field_name} must be positive")
        except (TypeError, ValueError):
            fail(errors, f"{pid}: hole series '{series_id}' slot_pattern.{field_name} missing or non-numeric")


    return errors


def validate_profile(profile: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []

    pid = profile.get("id") or f"<missing id at index {index}>"

    for field in REQUIRED_PROFILE_FIELDS:
        if field not in profile:
            fail(errors, f"{pid}: missing required field '{field}'")
        elif is_missing(profile.get(field)):
            fail(errors, f"{pid}: required field '{field}' is empty")

    geometry = profile.get("geometry")
    if not isinstance(geometry, dict):
        if "geometry" in profile:
            fail(errors, f"{pid}: geometry must be an object")
        return errors

    for field in REQUIRED_GEOMETRY_FIELDS:
        if field not in geometry:
            fail(errors, f"{pid}: geometry missing required field '{field}'")
        elif is_missing(geometry.get(field)):
            fail(errors, f"{pid}: geometry field '{field}' is empty")

    for field in REQUIRED_MM_VALUE_FIELDS:
        if not has_numeric_mm(geometry, field):
            fail(errors, f"{pid}: geometry.{field}.mm missing or non-numeric")

    gauge = profile.get("gauge")
    try:
        if int(gauge) <= 0:
            fail(errors, f"{pid}: gauge must be positive")
    except (TypeError, ValueError):
        fail(errors, f"{pid}: gauge must be an integer-like value")

    finishes = profile.get("finishes")
    if isinstance(finishes, list):
        if not finishes:
            fail(errors, f"{pid}: finishes must not be empty")
        for i, finish in enumerate(finishes):
            if not isinstance(finish, str) or not finish.strip():
                fail(errors, f"{pid}: finishes[{i}] must be a non-empty string")
    elif "finishes" in profile:
        fail(errors, f"{pid}: finishes must be a list")

    standard_lengths = profile.get("standard_lengths")
    if isinstance(standard_lengths, dict):
        has_any_lengths = False
        for key in ("ft", "m", "mm"):
            vals = standard_lengths.get(key)
            if isinstance(vals, list) and vals:
                has_any_lengths = True
                for i, val in enumerate(vals):
                    try:
                        if float(val) <= 0:
                            fail(errors, f"{pid}: standard_lengths.{key}[{i}] must be positive")
                    except (TypeError, ValueError):
                        fail(errors, f"{pid}: standard_lengths.{key}[{i}] must be numeric")
        if not has_any_lengths:
            fail(errors, f"{pid}: standard_lengths must include at least one non-empty list")
    elif "standard_lengths" in profile:
        fail(errors, f"{pid}: standard_lengths must be an object")

    profile_spec = geometry.get("profile_spec")
    if isinstance(profile_spec, dict):
        kind = profile_spec.get("kind")

        if kind == "u_channel_lipped":
            for field in REQUIRED_LIPPED_PROFILE_SPEC_FIELDS:
                if field not in profile_spec:
                    fail(errors, f"{pid}: geometry.profile_spec missing required field '{field}'")
                elif is_missing(profile_spec.get(field)):
                    fail(errors, f"{pid}: geometry.profile_spec field '{field}' is empty")

            for field in ("t", "lip_return"):
                val = get_nested(profile_spec, [field, "mm"])
                try:
                    if float(val) <= 0:
                        fail(errors, f"{pid}: geometry.profile_spec.{field}.mm must be positive")
                except (TypeError, ValueError):
                    fail(errors, f"{pid}: geometry.profile_spec.{field}.mm missing or non-numeric")

        elif kind is not None and not isinstance(kind, str):
            fail(errors, f"{pid}: geometry.profile_spec.kind must be a string")

    elif profile_spec is not None:
        fail(errors, f"{pid}: geometry.profile_spec must be an object")

    return errors


def main() -> int:
    if not PROFILES_JSON.exists():
        print(f"ERROR: missing file: {PROFILES_JSON}", file=sys.stderr)
        return 2

    if not MAPPING_HOLE_SERIES_JSON.exists():
        print(f"ERROR: missing file: {MAPPING_HOLE_SERIES_JSON}", file=sys.stderr)
        return 2

    try:
        profiles = load_profiles(PROFILES_JSON)
    except Exception as e:
        print(f"ERROR: failed to load {PROFILES_JSON}: {e}", file=sys.stderr)
        return 2

    try:
        hole_series = load_hole_series(MAPPING_HOLE_SERIES_JSON)
    except Exception as e:
        print(f"ERROR: failed to load {MAPPING_HOLE_SERIES_JSON}: {e}", file=sys.stderr)
        return 2

    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"profiles[{index}]: record must be an object")
            continue

        pid = profile.get("id")
        if pid:
            if pid in seen_ids:
                errors.append(f"{pid}: duplicate profile id")
            seen_ids.add(pid)

        errors.extend(validate_profile(profile, index))
        errors.extend(validate_piercing_series(profile, index, hole_series))

    if errors:
        print("profiles.json schema smoke test FAILED")
        print()
        for err in errors:
            print(f"- {err}")
        return 1

    print("profiles.json schema smoke test passed")
    print(f"validated {len(profiles)} profile record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
