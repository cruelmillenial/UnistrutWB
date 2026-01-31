"""
Profile geometry builders.

Two modes:
- simple: fast U-outline
- detailed: adds a crude lip approximation (still not exact to catalog)

Upgrade path:
- encode exact flange/lip radii and lips by profile family
- cut slot/hole patterns per pierced series (visual mode)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any

import FreeCAD as App
import Part

Mode = Literal["simple", "detailed"]

@dataclass
class BuildSpec:
    profile_id: str
    length_mm: float
    mode: Mode = "simple"

def _rect_profile(w: float, h: float) -> Part.Face:
    pts = [
        App.Vector(0, 0, 0),
        App.Vector(w, 0, 0),
        App.Vector(w, h, 0),
        App.Vector(0, h, 0),
        App.Vector(0, 0, 0),
    ]
    wire = Part.Wire(Part.makePolygon(pts))
    return Part.Face(wire)

def _rect_profile_yz(w: float, h: float) -> Part.Face:
    """
    Rectangle in the YZ plane (X=0). w -> Y extent, h -> Z extent.
    """
    pts = [
        App.Vector(0, 0, 0),
        App.Vector(0, w, 0),
        App.Vector(0, w, h),
        App.Vector(0, 0, h),
        App.Vector(0, 0, 0),
    ]
    wire = Part.Wire(Part.makePolygon(pts))
    return Part.Face(wire)


def build_channel(profile: Dict[str, Any], length_mm: float, mode: Mode = "simple") -> Part.Shape:
    geom = profile["geometry"]

    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(geom["thickness"]["mm"])

    # -------------------------------------------------
    # 🔀 DISPATCH: ETL-driven profile spec
    # -------------------------------------------------
    spec = geom.get("profile_spec") or {}
    if spec.get("kind") == "u_channel_lipped":
        t_mm = float(spec["t"]["mm"])
        lip_mm = float(spec["lip_return"]["mm"])
        return build_u_channel_lipped(
            width_mm=w,
            depth_mm=h,
            t_mm=t_mm,
            lip_mm=lip_mm,
            length_mm=length_mm,
        )

    # -------------------------------------------------
    # FALLBACK: existing crude U-channel logic
    # -------------------------------------------------

    outer = _rect_profile_yz(w, h)
    inner = _rect_profile_yz(max(w - 2*t, 0.1), max(h - t, 0.1))
    inner.translate(App.Vector(0, t, t))
    face = outer.cut(inner)

    solid = face.extrude(App.Vector(length_mm, 0, 0))

    if mode == "detailed":
        # crude in-turned lips: ridges that run along X (length)
        lip_w = min(6.0, w * 0.2)
        lip_t = min(2.0, t)

        left = Part.makeBox(length_mm, lip_w, lip_t)
        left.Placement = App.Placement(
            App.Vector(0, 0, h - lip_t),
            App.Rotation()
        )

        right = Part.makeBox(length_mm, lip_w, lip_t)
        right.Placement = App.Placement(
            App.Vector(0, w - lip_w, h - lip_t),
            App.Rotation()
        )

        solid = solid.fuse(left).fuse(right)

    return solid


def build_u_channel_lipped(
    width_mm: float,
    depth_mm: float,
    t_mm: float,
    lip_mm: float,
    length_mm: float,
) -> Part.Shape:
    """
    Lipped U-channel (MVP): base U-channel + two inward lip returns.
    Cross-section in YZ at X=0; extrusion along +X.

    width_mm: outside width (Y)
    depth_mm: outside depth/height (Z)
    t_mm: wall thickness
    lip_mm: inward return length from each top edge (Y direction)
    """
    w = float(width_mm)
    h = float(depth_mm)
    t = max(float(t_mm), 0.1)
    lip = max(float(lip_mm), 0.0)
    L = float(length_mm)

    # Clamp lip so it can't collide in the middle
    max_lip = max((w - 2 * t) / 2.0 - 0.1, 0.0)
    lip = min(lip, max_lip)

    # --- Base channel: outer minus inner cavity (open top)
    outer = _rect_profile_yz(w, h)
    inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
    inner.translate(App.Vector(0, t, t))
    face = outer.cut(inner)
    solid = face.extrude(App.Vector(L, 0, 0))

    if lip <= 0:
        return solid

    # --- Lip returns: two rectangular shelves at the top, running along X
    # They sit at the inner top edge (just below h), thickness t in Z.
    # Left lip spans Y: [t, t+lip]
    left = Part.makeBox(L, lip, t)
    left.Placement = App.Placement(
        App.Vector(0, t, h - t),
        App.Rotation()
    )

    # Right lip spans Y: [w - t - lip, w - t]
    right = Part.makeBox(L, lip, t)
    right.Placement = App.Placement(
        App.Vector(0, w - t - lip, h - t),
        App.Rotation()
    )

    return solid.fuse(left).fuse(right)

 


