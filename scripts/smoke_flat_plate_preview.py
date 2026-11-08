"""FreeCAD GUI smoke test for ETL reference plates, run in Python console via runpy.

runpy.run_path("/absolute/path/to/UnistrutWB/scripts/smoke_flat_plate_preview.py")
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import FreeCAD as App
import FreeCADGui as Gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Mod"))

from UnistrutWB.core.fittings import build_fitting_shape  # noqa: E402
from UnistrutWB.core.loader import Catalog  # noqa: E402


def main():
    catalog = Catalog.load(force_reload=True)
    doc = App.newDocument("FlatPlateReferenceSmoke")
    offset = 0.0
    ids = ("REF_P1065_SS33", "REF_P1066_SS33", "REF_P1067_SS33")
    for fitting_id in ids:
        row = catalog.get_fitting(fitting_id)
        assert row["record_status"] == "preview_only"
        geo = row["geometry"]
        shape = build_fitting_shape(row)
        assert not shape.isNull() and shape.isValid()
        assert len(shape.Solids) == 1
        assert abs(shape.BoundBox.XLength - geo["length_mm"]) < 0.01
        assert abs(shape.BoundBox.YLength - geo["width_mm"]) < 0.01
        assert abs(shape.BoundBox.ZLength - geo["thickness_mm"]) < 0.01
        hole_volume = sum(
            math.pi * (hole["diameter_mm"] / 2.0) ** 2 * geo["thickness_mm"]
            for hole in geo["holes"]
        )
        expected_volume = (
            geo["length_mm"] * geo["width_mm"] * geo["thickness_mm"] - hole_volume
        )
        assert abs(shape.Volume - expected_volume) < 0.01, (
            fitting_id, shape.Volume, expected_volume
        )
        obj = doc.addObject("Part::Feature", fitting_id)
        obj.Label = fitting_id + " [UNVERIFIED REFERENCE]"
        obj.Shape = shape
        obj.Placement.Base = App.Vector(offset, 0, 0)
        obj.addProperty("App::PropertyString", "ReferenceStatus", "ETL")
        obj.ReferenceStatus = row["record_status"]
        offset += geo["length_mm"] + 15.0
        print(
            f"PASS {fitting_id}: {len(geo['holes'])} actual through-holes; "
            f"shape valid, volume {shape.Volume:.3f} mm^3"
        )
    doc.recompute()
    Gui.activeDocument().activeView().viewAxonometric()
    Gui.activeDocument().activeView().fitAll()
    print("PASS: flat-plate reference preview smoke test (3 plates).")


if __name__ == "__main__":
    main()
