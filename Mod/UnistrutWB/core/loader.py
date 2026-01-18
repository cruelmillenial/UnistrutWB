"""
Datastore loader + small query helpers.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, Optional

import FreeCAD as App

DEFAULT_REL = "Mod/UnistrutWB/data/unistrut.json"

class CatalogError(RuntimeError):
    pass

class Catalog:
    def __init__(self, data: Dict[str, Any], mapping: Optional[Dict[str, Any]] = None):
        self.data = data
        self.mapping = mapping or {}

    @staticmethod
    def _user_data_path() -> Path:
        # UserAppData points to FreeCAD's user config dir
        return Path(App.ConfigGet("UserAppData"))

    @classmethod
    def load(cls, json_path: Optional[str] = None) -> "Catalog":
        base = cls._user_data_path()
        path = Path(json_path) if json_path else (base / DEFAULT_REL)
        if not path.exists():
            raise CatalogError(f"Missing datastore: {path}")
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        mapping_path = path.parent / "mapping_hole_series.json"
        mapping = {}
        if mapping_path.exists():
            with mapping_path.open("r", encoding="utf-8") as f:
                mapping = json.load(f)

        return cls(data=data, mapping=mapping)

    def get_profile(self, profile_id: str) -> Dict[str, Any]:
        for p in self.data.get("profiles", []):
            if p.get("id") == profile_id:
                return p
        raise CatalogError(f"Unknown profile_id: {profile_id}")

    def get_fitting(self, fitting_id: str) -> Dict[str, Any]:
        for f in self.data.get("fittings", []):
            if f.get("id") == fitting_id:
                return f
        raise CatalogError(f"Unknown fitting_id: {fitting_id}")

    def list_profiles(self) -> list[str]:
        return sorted([p.get("id") for p in self.data.get("profiles", []) if p.get("id")])

    def list_fittings(self) -> list[str]:
        return sorted([f.get("id") for f in self.data.get("fittings", []) if f.get("id")])

    def hole_series_factor(self, series_id: str) -> float:
        hs = (self.mapping or {}).get("hole_series", {})
        if series_id in hs and "beam_capacity_factor" in hs[series_id]:
            return float(hs[series_id]["beam_capacity_factor"])
        return 1.0
