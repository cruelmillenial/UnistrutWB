"""
Pydantic models (optional) for UnistrutWB datastore.

Run:
  pip install pydantic
  python -m schema.models validate ../Mod/UnistrutWB/data/unistrut.json
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class UnitVal(BaseModel):
    in_: Optional[float] = Field(default=None, alias="in")
    mm: Optional[float] = None

class Geometry(BaseModel):
    width: UnitVal
    height: UnitVal
    thickness: UnitVal
    lip: UnitVal
    corner_radius: UnitVal

class Provenance(BaseModel):
    source_pages: List[int] = Field(default_factory=list)
    table: Optional[str] = None
    notes: List[str] = Field(default_factory=list)

class Profile(BaseModel):
    id: str
    family: str
    gauge: Optional[int] = None
    geometry: Geometry
    mass: Dict[str, Optional[float]] = Field(default_factory=dict)
    finishes: List[str] = Field(default_factory=list)
    standard_lengths: Dict[str, List[float]] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance

class Datastore(BaseModel):
    meta: Dict[str, Any]
    profiles: List[Profile]
    pierced_variants: List[Dict[str, Any]] = Field(default_factory=list)
    fittings: List[Dict[str, Any]] = Field(default_factory=list)
    hardware: List[Dict[str, Any]] = Field(default_factory=list)
    finishes: List[Dict[str, Any]] = Field(default_factory=list)
    load_tables: List[Dict[str, Any]] = Field(default_factory=list)

def validate(path: str) -> Datastore:
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Datastore.model_validate(data)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        raise SystemExit("usage: python models.py <path-to-unistrut.json>")
    ds = validate(sys.argv[1])
    print(f"OK: {len(ds.profiles)} profiles, {len(ds.fittings)} fittings")
