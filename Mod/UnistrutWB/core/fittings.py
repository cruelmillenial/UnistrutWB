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
import json

def build_fitting_shape(fitting: Dict[str, Any]) -> Part.Shape:
    typ = fitting.get("geometry_type") or fitting.get("type", "")

    if typ == "splice_plate":
        return _build_splice_plate(fitting)

    if typ == "angle_plate":
        return _build_angle_plate(fitting)

    raise ValueError(f"Unknown fitting type: {typ}")


def _build_splice_plate(fitting: Dict[str, Any]) -> Part.Shape:
    """Build a centered flat plate; cut documented holes when ETL geometry is supplied.

    The shared ETL contract is corner-origin X=length, Y=width, Z=thickness.
    FreeCAD uses a centered XY shape with the mounting face at local Z=0.
    Legacy placeholder records without ETL geometry remain unchanged.
    """
    geometry = fitting.get("geometry")
    if geometry is None:
        w = float(fitting["width_mm"])
        h = float(fitting["height_mm"])
        t = float(fitting["thickness_mm"])
        face = Part.makePlane(w, h, App.Vector(-w / 2.0, -h / 2.0, 0))
        return face.extrude(App.Vector(0, 0, -t))

    if geometry.get("family") != "flat_splice_plate":
        raise ValueError("Unsupported ETL splice-plate family")
    length = float(geometry["length_mm"])
    width = float(geometry["width_mm"])
    thickness = float(geometry["thickness_mm"])
    if min(length, width, thickness) <= 0:
        raise ValueError("Plate dimensions must be positive")
    holes = geometry.get("holes")
    if not isinstance(holes, list) or not holes:
        raise ValueError("ETL plate must specify actual holes")

    shape = Part.makeBox(
        length, width, thickness,
        App.Vector(-length / 2.0, -width / 2.0, -thickness),
    )
    seen = []
    for index, hole in enumerate(holes):
        if hole.get("shape") != "round":
            raise ValueError(f"Unsupported hole shape at index {index}")
        x = float(hole["x_mm"])
        y = float(hole["y_mm"])
        diameter = float(hole["diameter_mm"])
        radius = diameter / 2.0
        if not (diameter > 0 and radius < x < length - radius
                and radius < y < width - radius):
            raise ValueError(f"Hole {index} crosses plate boundary")
        for other_x, other_y, other_radius in seen:
            if (x - other_x) ** 2 + (y - other_y) ** 2 <= (radius + other_radius) ** 2:
                raise ValueError(f"Hole {index} overlaps another hole")
        seen.append((x, y, radius))
        cutter = Part.makeCylinder(
            radius, thickness + 0.2,
            App.Vector(x - length / 2.0, y - width / 2.0, -thickness - 0.1),
            App.Vector(0, 0, 1),
        )
        shape = shape.cut(cutter)
    if shape.isNull() or not shape.isValid() or len(shape.Solids) != 1:
        raise ValueError("Generated fitting is not a valid single solid")
    return shape

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

    if "MateFrameMetadata" not in obj.PropertiesList:
        obj.addProperty(
            "App::PropertyString",
            "MateFrameMetadata",
            "Unistrut",
            "Serialized mate frame metadata"
        )

    obj.MateFrames = [f.get("id", "") for f in frames]
    obj.MateFrameMetadata = json.dumps(frames, sort_keys=True)