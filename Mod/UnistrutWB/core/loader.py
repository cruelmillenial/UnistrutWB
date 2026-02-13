# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import FreeCAD as App


def _data_dir() -> Path:
    # Workbench data folder (inside the repo)
    here = Path(__file__).resolve()
    return (here.parent.parent / "data").resolve()


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_datastore() -> Dict[str, Any]:
    """
    Canonical loader.

    Returns a unified in-memory structure:
      {
        "schema_version": ...,
        "profiles": { "<id>": {...}, ... },
        "fittings": { "<id>": {...}, ... },
        "finishes": { "<code>": {...}, ... }   # optional
      }

    Supports:
    - split JSON files: profiles.json, fittings.json, finishes.json
    - fallback: unistrut.json / datastore.json that contains top-level lists
    """
    d = _data_dir()

    # Preferred split files
    profiles_p = d / "profiles.json"
    fittings_p = d / "fittings.json"
    finishes_p = d / "finishes.json"

    # --- PROFILES (normalize list->dict and ensure geometry key) ---
    if profiles_p.exists():
        raw = _load_json(profiles_p)

        # Accept either:
        # A) {"schema_version": 1, "profiles": [ {...}, {...} ]}
        # B) {"P4100": {...}, "P1000": {...}}  (legacy dict keyed by id)
        if isinstance(raw, dict) and "profiles" in raw:
            profiles_list = raw.get("profiles", [])
            if not isinstance(profiles_list, list):
                raise TypeError(f"profiles.json: expected 'profiles' list, got {type(profiles_list)}")

            profiles_map: Dict[str, Dict[str, Any]] = {}
            for rec in profiles_list:
                if not isinstance(rec, dict):
                    raise TypeError(f"profiles.json: profile record must be object; got {type(rec)}")
                pid = rec.get("id")
                if not pid:
                    raise KeyError(f"profiles.json: profile record missing 'id': {rec}")
                if pid in profiles_map:
                    raise KeyError(f"profiles.json: duplicate profile id '{pid}'")
                profiles_map[pid] = rec

        elif isinstance(raw, dict):
            profiles_map = raw  # legacy dict keyed by id
        else:
            raise TypeError(f"profiles.json: unexpected top-level type {type(raw)}")

        # Ensure downstream contract: profile["geometry"]
        for pid, rec in profiles_map.items():
            if not isinstance(rec, dict):
                raise TypeError(f"profiles[{pid}]: expected object; got {type(rec)}")

            geom = rec.get("geometry")
            if geom is None:
                raise KeyError(f"profiles[{pid}] missing 'geometry'; keys={sorted(rec.keys())}")
            if not isinstance(geom, dict):
                raise TypeError(f"profiles[{pid}].geometry must be object; got {type(geom)}")

            # Merge top-level profile_spec/spec into geometry.profile_spec if present
            if "profile_spec" in rec and "profile_spec" not in geom:
                geom["profile_spec"] = rec["profile_spec"]
            elif "spec" in rec and "profile_spec" not in geom:
                geom["profile_spec"] = rec["spec"]

        ds["profiles"] = profiles_map


    # profiles.json expected shape:
    # { "schema_version": <int>, "profiles": [ {...}, {...} ] }

    profiles_raw = _read_json(profiles_p)

    # schema version (optional to keep)
    profiles_schema_version = profiles_raw.get("schema_version", None)

    profiles_list = profiles_raw.get("profiles", [])
    if not isinstance(profiles_list, list):
        raise TypeError(f"profiles.json: expected 'profiles' to be a list, got {type(profiles_list)}")
    
    # Convert list -> dict keyed by id
    profiles: dict[str, dict] = {}
    for rec in profiles_list:
        pid = rec.get("id")
        if not pid:
            raise KeyError(f"profiles.json: profile record missing 'id': {rec}")
        if pid in profiles:
            raise KeyError(f"profiles.json: duplicate profile id '{pid}'")
        profiles[pid] = rec

    # Legacy monolith candidates
    legacy_candidates = [
        d / "unistrut.json",
        d / "datastore.json",
        d / "unistrut_datastore.json",
    ]

    ds: Dict[str, Any] = {
        "schema_version": 1,
        "profiles": {},
        "fittings": {},
        "finishes": {},
    }

    if profiles_p.exists() or fittings_p.exists() or finishes_p.exists():
        if profiles_p.exists():
            raw = _load_json(profiles_p)
            ds["schema_version"] = raw.get("schema_version", ds["schema_version"])
            items = raw.get("profiles", raw)  # allow either {"profiles":[...]} or just [...]
            if isinstance(items, list):
                for p in items:
                    pid = p.get("id")
                    if pid:
                        ds["profiles"][pid] = p

        if fittings_p.exists():
            raw = _load_json(fittings_p)
            ds["schema_version"] = raw.get("schema_version", ds["schema_version"])
            items = raw.get("fittings", raw)
            if isinstance(items, list):
                for f in items:
                    fid = f.get("id")
                    if fid:
                        ds["fittings"][fid] = f

        if finishes_p.exists():
            raw = _load_json(finishes_p)
            ds["schema_version"] = raw.get("schema_version", ds["schema_version"])
            items = raw.get("finishes", raw)
            if isinstance(items, list):
                for fin in items:
                    code = fin.get("code")
                    if code:
                        ds["finishes"][code] = fin

        return ds

    # Fallback: legacy monolith
    legacy_path: Optional[Path] = None
    for p in legacy_candidates:
        if p.exists():
            legacy_path = p
            break

    if legacy_path is None:
        # No data available; return empty
        return ds

    raw = _load_json(legacy_path)
    ds["schema_version"] = raw.get("schema_version", ds["schema_version"])

    for p in raw.get("profiles", []):
        pid = p.get("id")
        if pid:
            ds["profiles"][pid] = p

    for f in raw.get("fittings", []):
        fid = f.get("id")
        if fid:
            ds["fittings"][fid] = f

    for fin in raw.get("finishes", []):
        code = fin.get("code")
        if code:
            ds["finishes"][code] = fin

    return ds


@dataclass(frozen=True)
class Catalog:
    _ds: Dict[str, Any]

    _cached: Optional["Catalog"] = None

    @classmethod
    def load(cls, force_reload: bool = False) -> "Catalog":
        if (not force_reload) and cls._cached is not None:
            return cls._cached
        cat = cls(load_datastore())
        cls._cached = cat
        return cat

    # ---- Fittings API used by cmd_add_fitting.py
    def list_fittings(self) -> List[str]:
        return sorted(self._ds.get("fittings", {}).keys())

    def get_fitting(self, fitting_id: str) -> Dict[str, Any]:
        fittings = self._ds.get("fittings", {})
        if fitting_id not in fittings:
            raise KeyError(f"Unknown fitting id: {fitting_id}")
        return fittings[fitting_id]

    # ---- Profiles (for later UI wiring / parity)
    def list_profiles(self) -> List[str]:
        return sorted(self._ds.get("profiles", {}).keys())

    def get_profile(self, profile_id: str) -> Dict[str, Any]:
        profiles = self._ds.get("profiles", {})
        if profile_id not in profiles:
            raise KeyError(f"Unknown profile id: {profile_id}")
        return profiles[profile_id]
