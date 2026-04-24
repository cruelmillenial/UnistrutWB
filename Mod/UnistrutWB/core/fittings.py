"""
Fitting geometry + mate metadata.

MVP approach:
- simple parametric solids
- metadata for future snapping/placement
- not catalog-perfect geometry yet
"""
from __future__ import annotations
from typing import Dict, Any

import FreeCAD as App
import Part


def build_fitting_shape(fitting: Dict[str, Any]) -> Part.Shape:
    typ = fitting.get("type", "")

    if typ == "splice_plate":
        return _build_splice_plate(fitting)

    if typ == "angle_plate":
        return _build_angle_plate(fitting)

    raise ValueError(f"Unknown fitting type: {typ}")


def _build_splice_plate(fitting: Dict[str, Any]) -> Part.Shape:
    w = float(fitting["width_mm"])
    h = float(fitting["height_mm"])
    t = float(fitting["thickness_mm"])

    # Center plate on local origin in XY, thickness in +Z
    face = Part.makePlane(w, h, App.Vector(-w / 2.0, -h / 2.0, 0))
    return face.extrude(App.Vector(0, 0, t))


def _build_angle_plate(fitting: Dict[str, Any]) -> Part.Shape:
    a = float(fitting["leg_a_mm"])
    b = float(fitting["leg_b_mm"])
    width = float(fitting["width_mm"])
    t = float(fitting["thickness_mm"])

    leg_a = Part.makeBox(a, t, width, App.Vector(0, 0, 0))
    leg_b = Part.makeBox(t, b, width, App.Vector(0, 0, 0))

    return leg_a.fuse(leg_b)

def add_mate_markers(obj, fitting: Dict[str, Any]) -> None:
    frames = fitting.get("mate_frames", [])

    if "MateFrames" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyStringList",
            "MateFrames",
            "Unistrut",
            "Available mate frame identifiers"
        )

    obj.MateFrames = [f.get("id", "") for f in frames]