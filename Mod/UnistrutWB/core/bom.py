"""
BOM / Cut list aggregation and export.

Counts:
- profiles: by ProfileId + Finish + (rounded) Length
- fittings: by FittingId
- hardware: (not yet inferred) reserved

Export: CSV with headers:
type,id,finish,length_mm,qty,part_key
"""
from __future__ import annotations

import csv
from collections import defaultdict
from typing import Dict, Any, Tuple
import FreeCAD as App


def _key_profile(obj) -> Tuple[str, str, int]:
    pid = getattr(obj, "ProfileId", "")
    finish = getattr(obj, "Finish", "")
    length = getattr(obj, "Length", None)
    length_mm = int(round(float(length.Value))) if length is not None else 0
    return (pid, finish, length_mm)


def _part_key(row: Dict[str, Any]) -> str:
    # Stable, explicit join key for downstream tooling.
    # fittings ignore finish/length; profiles include both.
    t = row.get("type", "")
    i = row.get("id", "")
    fin = row.get("finish", "")
    L = row.get("length_mm", 0)
    if t == "profile":
        return f"profile:{i}:{fin}:{int(L)}"
    return f"{t}:{i}"


def aggregate(doc=None) -> list[Dict[str, Any]]:
    doc = doc or App.ActiveDocument
    rows: list[Dict[str, Any]] = []
    if doc is None:
        return rows

    counts = defaultdict(int)

    for obj in doc.Objects:
        if not hasattr(obj, "UnistrutType"):
            continue

        if obj.UnistrutType == "profile":
            key = ("profile",) + _key_profile(obj)
            counts[key] += 1

        elif obj.UnistrutType == "fitting":
            fid = getattr(obj, "FittingId", "") or getattr(obj, "Label", "") or obj.Name
            key = ("fitting", fid)
            counts[key] += 1

    for k, qty in counts.items():
        if k[0] == "profile":
            _, pid, finish, length_mm = k
            row = {
                "type": "profile",
                "id": pid,
                "finish": finish,
                "length_mm": length_mm,
                "qty": qty,
            }
            row["part_key"] = _part_key(row)
            rows.append(row)
        else:
            _, fid = k
            row = {
                "type": "fitting",
                "id": fid,
                "finish": "",
                "length_mm": "",
                "qty": qty,
            }
            row["part_key"] = _part_key(row)
            rows.append(row)

    rows.sort(key=lambda r: (r["type"], r["id"], str(r["finish"]), str(r["length_mm"])))
    return rows


def export_csv(path: str, doc=None) -> None:
    rows = aggregate(doc)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["type", "id", "finish", "length_mm", "qty", "part_key"],
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)
