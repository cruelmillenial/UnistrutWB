"""
BOM / Cut list aggregation and export.

Counts:
- profiles: by ProfileId + Finish + (rounded) Length
- fittings: by FittingId
- hardware: (not yet inferred) reserved

Export: CSV with headers:
type,id,finish,length_mm,qty
"""
from __future__ import annotations
import csv
from collections import defaultdict
from typing import Dict, Any, Tuple
import FreeCAD as App

def _key_profile(obj) -> Tuple[str,str,int]:
    pid = getattr(obj, "ProfileId", "")
    finish = getattr(obj, "Finish", "")
    length = getattr(obj, "Length", None)
    length_mm = int(round(float(length.Value))) if length is not None else 0
    return (pid, finish, length_mm)

def aggregate(doc=None) -> list[Dict[str, Any]]:
    doc = doc or App.ActiveDocument
    rows = []
    if doc is None:
        return rows

    counts = defaultdict(int)

    for obj in doc.Objects:
        if hasattr(obj, "UnistrutType"):
            if obj.UnistrutType == "profile":
                key = ("profile",) + _key_profile(obj)
                counts[key] = counts.get(key, 0) + 1
            elif obj.UnistrutType == "fitting":
                fid = getattr(obj, "FittingId", "") or getattr(obj, "Label", "") or obj.Name
                key = ("fitting", fid)
                counts[key] = counts.get(key, 0) + 1

    for k, qty in counts.items():
        if k[0] == "profile":
            _, pid, finish, length_mm = k
            rows.append({"type":"profile","id":pid,"finish":finish,"length_mm":length_mm,"qty":qty})
        else:
            _, fid = k
            rows.sort(key=lambda r: (r["type"], r["id"], str(r["finish"]), str(r["length_mm"])))

    return rows

def export_csv(path: str, doc=None) -> None:
    rows = aggregate(doc)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["type","id","finish","length_mm","qty"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
