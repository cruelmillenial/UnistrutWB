#!/usr/bin/env python3
"""Validate UnistrutWB raw and normalized JSON catalog records.

Runs without FreeCAD or third-party packages.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Finding:
    level: str
    path: str
    message: str

    def __str__(self) -> str:
        marker = "ERROR" if self.level == "error" else "WARN"
        return f"{marker}: {self.path}: {self.message}"


class Validator:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.findings: list[Finding] = []
        self.raw_source_ids: dict[str, Path] = {}
        self.raw_record_ids: dict[str, Path] = {}
        self.normalized_ids: dict[str, Path] = {}

    def error(self, path: str, message: str) -> None:
        self.findings.append(Finding("error", path, message))

    def warn(self, path: str, message: str) -> None:
        self.findings.append(Finding("warning", path, message))

    def load_json(self, path: Path) -> Any | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            self.error(str(path), "file not found")
        except json.JSONDecodeError as exc:
            self.error(str(path), f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        except OSError as exc:
            self.error(str(path), f"could not read file: {exc}")
        return None

    def require_dict(self, value: Any, path: str) -> dict[str, Any] | None:
        if not isinstance(value, dict):
            self.error(path, "must be an object")
            return None
        return value

    def require_list(self, value: Any, path: str) -> list[Any] | None:
        if not isinstance(value, list):
            self.error(path, "must be an array")
            return None
        return value

    def require_nonempty_string(self, obj: dict[str, Any], key: str, path: str) -> str | None:
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            self.error(f"{path}.{key}", "must be a non-empty string")
            return None
        return value

    def require_positive_number(self, obj: dict[str, Any], key: str, path: str) -> float | None:
        value = obj.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            self.error(f"{path}.{key}", "must be a finite positive number")
            return None
        return float(value)

    def check_schema_version(self, obj: dict[str, Any], path: str) -> None:
        if obj.get("schema_version") != 1:
            self.error(f"{path}.schema_version", "must equal 1")

    def check_unit_pair(self, obj: Any, path: str, imperial_key: str = "in", metric_key: str = "mm", tolerance: float = 0.03) -> None:
        unit_obj = self.require_dict(obj, path)
        if unit_obj is None:
            return
        metric = unit_obj.get(metric_key)
        imperial = unit_obj.get(imperial_key)
        if metric is None and imperial is None:
            self.error(path, f"must contain '{metric_key}' and/or '{imperial_key}'")
            return
        metric_value = None
        imperial_value = None
        if metric is not None:
            metric_value = self.require_positive_number(unit_obj, metric_key, path)
        if imperial is not None:
            imperial_value = self.require_positive_number(unit_obj, imperial_key, path)
        if metric_value is not None and imperial_value is not None:
            expected = imperial_value * 25.4
            relative = abs(metric_value - expected) / expected
            if relative > tolerance:
                self.error(path, f"unit mismatch: {imperial_value} in converts to {expected:.4g} mm, not {metric_value} mm")

    def register_unique(self, registry: dict[str, Path], item_id: str, file_path: Path, logical_path: str) -> None:
        previous = registry.get(item_id)
        if previous is not None:
            self.error(logical_path, f"duplicate id '{item_id}' (also in {previous})")
        else:
            registry[item_id] = file_path

    def validate_raw_file(self, path: Path) -> None:
        doc = self.load_json(path)
        root = self.require_dict(doc, str(path))
        if root is None:
            return
        self.check_schema_version(root, str(path))

        source = self.require_dict(root.get("source"), f"{path}.source")
        if source is None:
            return
        source_id = self.require_nonempty_string(source, "id", f"{path}.source")
        self.require_nonempty_string(source, "file", f"{path}.source")
        self.require_nonempty_string(source, "title", f"{path}.source")
        sha = self.require_nonempty_string(source, "sha256", f"{path}.source")
        if sha and not SHA256_RE.fullmatch(sha):
            self.error(f"{path}.source.sha256", "must be a lowercase 64-character SHA-256 digest")
        pages = self.require_list(source.get("pages_used"), f"{path}.source.pages_used")
        if pages is not None and (not pages or any(not isinstance(page, int) or page < 1 for page in pages)):
            self.error(f"{path}.source.pages_used", "must contain positive page numbers")
        if source_id:
            self.register_unique(self.raw_source_ids, source_id, path, f"{path}.source.id")

        extraction = self.require_dict(root.get("extraction"), f"{path}.extraction")
        if extraction is None:
            return
        self.require_nonempty_string(extraction, "method", f"{path}.extraction")
        status = self.require_nonempty_string(extraction, "status", f"{path}.extraction")
        if status and status not in {"draft", "reviewed", "verified"}:
            self.error(f"{path}.extraction.status", "must be draft, reviewed, or verified")
        records = self.require_list(extraction.get("records"), f"{path}.extraction.records")
        if records is None:
            return
        if not records:
            self.error(f"{path}.extraction.records", "must not be empty")
        for index, record_value in enumerate(records):
            record_path = f"{path}.extraction.records[{index}]"
            record = self.require_dict(record_value, record_path)
            if record is None:
                continue
            record_id = self.require_nonempty_string(record, "id", record_path)
            page = record.get("page")
            if not isinstance(page, int) or page < 1:
                self.error(f"{record_path}.page", "must be a positive integer")
            elif pages is not None and page not in pages:
                self.warn(f"{record_path}.page", "is not listed in source.pages_used")
            if record_id:
                self.register_unique(self.raw_record_ids, record_id, path, f"{record_path}.id")

    def validate_profile(self, profile_value: Any, index: int, path: Path) -> None:
        logical = f"{path}.profiles[{index}]"
        profile = self.require_dict(profile_value, logical)
        if profile is None:
            return
        profile_id = self.require_nonempty_string(profile, "id", logical)
        if profile_id:
            self.register_unique(self.normalized_ids, profile_id, path, f"{logical}.id")
        self.require_nonempty_string(profile, "family", logical)
        gauge = profile.get("gauge")
        if isinstance(gauge, bool) or not isinstance(gauge, (int, float)) or gauge <= 0:
            self.error(f"{logical}.gauge", "must be a positive number")

        geometry = self.require_dict(profile.get("geometry"), f"{logical}.geometry")
        if geometry is not None:
            for field in ("width", "height", "thickness"):
                self.check_unit_pair(geometry.get(field), f"{logical}.geometry.{field}")
            piercing = self.require_dict(geometry.get("piercing"), f"{logical}.geometry.piercing")
            if piercing is not None:
                series = piercing.get("series")
                if series is not None and not isinstance(series, str):
                    self.error(f"{logical}.geometry.piercing.series", "must be a string or null")
                if not isinstance(piercing.get("overrides"), dict):
                    self.error(f"{logical}.geometry.piercing.overrides", "must be an object")
            spec = self.require_dict(geometry.get("profile_spec"), f"{logical}.geometry.profile_spec")
            if spec is not None:
                self.require_nonempty_string(spec, "kind", f"{logical}.geometry.profile_spec")
                self.check_unit_pair(spec.get("t"), f"{logical}.geometry.profile_spec.t")
                self.check_unit_pair(spec.get("lip_return"), f"{logical}.geometry.profile_spec.lip_return")
                thickness = geometry.get("thickness")
                if isinstance(thickness, dict) and isinstance(spec.get("t"), dict):
                    for unit in ("mm", "in"):
                        a, b = thickness.get(unit), spec["t"].get(unit)
                        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) > 1e-9:
                            self.error(f"{logical}.geometry.profile_spec.t.{unit}", "must match geometry.thickness")

        finishes = self.require_list(profile.get("finishes"), f"{logical}.finishes")
        if finishes is not None:
            if not finishes:
                self.error(f"{logical}.finishes", "must not be empty")
            if any(not isinstance(item, str) or not item for item in finishes):
                self.error(f"{logical}.finishes", "must contain non-empty strings")
            if len(finishes) != len(set(finishes)):
                self.error(f"{logical}.finishes", "must not contain duplicates")

        lengths = self.require_dict(profile.get("standard_lengths"), f"{logical}.standard_lengths")
        if lengths is not None:
            feet = self.require_list(lengths.get("ft"), f"{logical}.standard_lengths.ft")
            metres = self.require_list(lengths.get("m"), f"{logical}.standard_lengths.m")
            if feet is not None and metres is not None:
                if len(feet) != len(metres) or not feet:
                    self.error(f"{logical}.standard_lengths", "ft and m arrays must be non-empty and equal in length")
                else:
                    for pos, (ft, m) in enumerate(zip(feet, metres)):
                        if not isinstance(ft, (int, float)) or not isinstance(m, (int, float)) or ft <= 0 or m <= 0:
                            self.error(f"{logical}.standard_lengths[{pos}]", "length values must be positive numbers")
                        elif abs(m - ft * 0.3048) / (ft * 0.3048) > 0.01:
                            self.error(f"{logical}.standard_lengths[{pos}]", f"unit mismatch: {ft} ft does not correspond to {m} m")

        provenance = profile.get("provenance")
        if provenance is not None:
            prov = self.require_dict(provenance, f"{logical}.provenance")
            if prov is not None:
                source_id = self.require_nonempty_string(prov, "source_id", f"{logical}.provenance")
                self.require_nonempty_string(prov, "source_file", f"{logical}.provenance")
                digest = self.require_nonempty_string(prov, "source_sha256", f"{logical}.provenance")
                if digest and not SHA256_RE.fullmatch(digest):
                    self.error(f"{logical}.provenance.source_sha256", "must be a lowercase 64-character SHA-256 digest")
                pages = self.require_list(prov.get("source_pages"), f"{logical}.provenance.source_pages")
                if pages is not None and (not pages or any(not isinstance(page, int) or page < 1 for page in pages)):
                    self.error(f"{logical}.provenance.source_pages", "must contain positive page numbers")
                if source_id and source_id not in self.raw_source_ids:
                    self.error(f"{logical}.provenance.source_id", f"references missing raw source '{source_id}'")
                elif source_id:
                    raw_path = self.raw_source_ids[source_id]
                    raw_doc = self.load_json(raw_path)
                    if isinstance(raw_doc, dict) and isinstance(raw_doc.get("source"), dict):
                        raw_source = raw_doc["source"]
                        if digest and raw_source.get("sha256") != digest:
                            self.error(f"{logical}.provenance.source_sha256", "does not match raw source digest")
                        if prov.get("source_file") != raw_source.get("file"):
                            self.error(f"{logical}.provenance.source_file", "does not match raw source file")

    def validate_profiles_file(self, path: Path) -> None:
        doc = self.load_json(path)
        root = self.require_dict(doc, str(path))
        if root is None:
            return
        self.check_schema_version(root, str(path))
        profiles = self.require_list(root.get("profiles"), f"{path}.profiles")
        if profiles is None:
            return
        if not profiles:
            self.error(f"{path}.profiles", "must not be empty")
        for index, profile in enumerate(profiles):
            self.validate_profile(profile, index, path)

    def validate(self) -> list[Finding]:
        raw_dir = self.data_dir / "raw"
        raw_files = sorted(raw_dir.rglob("*.json")) if raw_dir.exists() else []
        for path in raw_files:
            self.validate_raw_file(path)

        profiles_path = self.data_dir / "profiles.json"
        self.validate_profiles_file(profiles_path)

        for normalized_id, normalized_path in self.normalized_ids.items():
            if normalized_id not in self.raw_record_ids:
                self.warn(f"{normalized_path}:{normalized_id}", "has no raw record yet")
        return self.findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "Mod" / "UnistrutWB" / "data",
        help="catalog data directory (default: repository Mod/UnistrutWB/data)",
    )
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validator = Validator(args.data_dir.resolve())
    findings = validator.validate()
    errors = [item for item in findings if item.level == "error"]
    warnings = [item for item in findings if item.level == "warning"]

    for finding in findings:
        print(finding)

    profile_count = len(validator.normalized_ids)
    source_count = len(validator.raw_source_ids)
    record_count = len(validator.raw_record_ids)
    failed = bool(errors or (args.strict and warnings))
    status = "FAIL" if failed else "PASS"
    print(f"{status}: {profile_count} normalized profiles, {source_count} raw sources, {record_count} raw records; {len(errors)} errors, {len(warnings)} warnings")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
