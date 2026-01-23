"""
Transform layer (Staging -> Canonical).

Uses pandas to:
- normalize typing
- compute dual units (imperial + SI)
- enforce required keys
- attach provenance arrays
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

IN_TO_MM = 25.4
FT_TO_M = 0.3048
LBFT_TO_KGM = 1.48816394357  # lb/ft -> kg/m

def _csv_list(s: str) -> list[str]:
    if s is None or (isinstance(s, float) and pd.isna(s)) or str(s).strip() == "":
        return []
    return [x.strip() for x in str(s).split(",") if x.strip()]

def load_staging(staging_dir: str) -> dict:
    p = Path(staging_dir)
    profiles = pd.read_csv(p / "profiles_seed.csv")
    finishes = pd.read_csv(p / "finishes_seed.csv")
    torque = pd.read_csv(p / "torque_seed.csv")
    fittings = pd.read_csv(p / "fittings_seed.csv")
    return {"profiles": profiles, "finishes": finishes, "torque": torque, "fittings": fittings}

def enrich_profile_spec(profile: dict) -> dict:
    """
    ETL-derived geometry enrichment (transform rules).
    NOT manual per-product edits in the JSON.
    """
    pid = (profile.get("id") or profile.get("profile_id") or "").upper()
    geom = profile.setdefault("geometry", {})

    def _in_to_mm(x):  # local helper
        return float(x) * 25.4

    # If already specified, do nothing
    spec = geom.get("profile_spec")
    if isinstance(spec, dict) and spec.get("kind"):
        return profile

    # Rule: P4100 gets a lipped U-channel spec (placeholder dims until extracted)
    if pid == "P4100":
        t_in = None
        if isinstance(geom.get("thickness"), dict):
            t_in = geom["thickness"].get("in")

        if t_in is None:
            t_in = 0.105  # placeholder

        lip_in = 0.375   # placeholder return length
        r_in = 0.060     # placeholder inside radius (optional; may be unused)

        geom["profile_spec"] = {
            "kind": "u_channel_lipped",
            "t": {"in": float(t_in), "mm": _in_to_mm(t_in)},
            "lip_return": {"in": float(lip_in), "mm": _in_to_mm(lip_in)},
            "inside_radius": {"in": float(r_in), "mm": _in_to_mm(r_in)},
        }

    return profile

def transform(staging: dict, meta: dict) -> dict:
    profiles_df = staging["profiles"].copy()
    finishes_df = staging["finishes"].copy()
    torque_df = staging["torque"].copy()
    fittings_df = staging["fittings"].copy()

    profiles = []
    for _, r in profiles_df.iterrows():
        w_in = float(r["width_in"])
        h_in = float(r["height_in"])
        t_in = float(r["thickness_in"])
        prof = {
            "id": str(r["id"]).strip(),
            "family": str(r["family"]).strip(),
            "gauge": int(r["gauge"]) if not pd.isna(r["gauge"]) else None,
            "geometry": {
                "width": {"in": w_in, "mm": w_in * IN_TO_MM},
                "height": {"in": h_in, "mm": h_in * IN_TO_MM},
                "thickness": {"in": t_in, "mm": t_in * IN_TO_MM},
                "lip": {"in": None, "mm": None},
                "corner_radius": {"in": None, "mm": None},
            },
            "mass": {"lb_per_ft": None, "kg_per_m": None},
            "finishes": _csv_list(r.get("finishes_csv","")),
            "standard_lengths": {
                "ft": [float(x) for x in _csv_list(r.get("std_lengths_ft_csv",""))],
                "m": [float(x) * FT_TO_M for x in _csv_list(r.get("std_lengths_ft_csv",""))],
            },
            "properties": {"section": {}, "material": {}},
            "provenance": {
                "source_pages": [int(x) for x in _csv_list(r.get("source_pages_csv",""))],
                "table": None,
                "notes": _csv_list(r.get("notes","")),
            },
        }
        profiles.append(prof)

    profiles = [enrich_profile_spec(p) for p in profiles]

    finishes = []
    for _, r in finishes_df.iterrows():
        finishes.append({
            "code": str(r["code"]).strip(),
            "name": str(r["name"]).strip(),
            "standards": [x.strip() for x in str(r.get("standards_csv","")).split(";") if x.strip()],
            "provenance": {"source_pages": [int(x) for x in _csv_list(r.get("source_pages_csv",""))], "notes": _csv_list(r.get("notes",""))},
        })

    hardware = []
    for _, r in torque_df.iterrows():
        hardware.append({
            "id": f"TORQUE_{str(r['thread']).replace('/','_').replace(' ','')}",
            "kind": "torque_spec",
            "thread": str(r["thread"]).strip(),
            "torque": {
                "ft_lb_rec": float(r["rec_ft_lb"]),
                "N_m_rec": float(r["rec_N_m"]),
                "ft_lb_max": float(r["max_ft_lb"]),
                "N_m_max": float(r["max_N_m"]),
            },
            "provenance": {"source_pages": [int(x) for x in _csv_list(r.get("source_pages_csv",""))], "notes": _csv_list(r.get("notes",""))},
        })

    fittings = []
    for _, r in fittings_df.iterrows():
        t_in = float(r["thickness_in"])
        d_in = float(r["hole_diam_in"])
        fittings.append({
            "id": str(r["id"]).strip(),
            "name": str(r["name"]).strip(),
            "category": str(r["category"]).strip(),
            "thickness": {"in": t_in, "mm": t_in * IN_TO_MM},
            "holes": [{"diameter": {"in": d_in, "mm": d_in * IN_TO_MM}, "pattern": str(r.get("hole_pattern","")).strip()}],
            "mate_frames": [
                {"id": "A", "kind": "LCS", "description": "Mount face"},
                {"id": "B", "kind": "LCS", "description": "Channel face"},
            ],
            "provenance": {"source_pages": [int(x) for x in _csv_list(r.get("source_pages_csv",""))], "notes": _csv_list(r.get("notes",""))},
        })

    ds = {
        "meta": meta,
        "profiles": profiles,
        "pierced_variants": [],  # filled by rules file in load step
        "fittings": fittings,
        "hardware": hardware,
        "finishes": finishes,
        "load_tables": [],
    }
    return ds
