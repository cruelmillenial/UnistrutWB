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
from typing import Literal, Dict, Any
from .holes import apply_hole_series, resolve_piercing_spec

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

def _compute_slot_centers_web(
    *,
    length_mm: float,
    width_mm: float,
    thickness_mm: float,
    series_code: str,
) -> list[App.Vector]:
    m = _load_hole_series_map()
    hs = (m.get("hole_series") or {}).get(series_code) or {}
    pat = hs.get("slot_pattern")
    if not pat:
        return []

    L = float(length_mm)
    w = float(width_mm)
    t = float(thickness_mm)

    pitch = float(pat["pitch_mm"])
    end_margin = float(pat.get("end_margin_mm", pitch / 2.0))
    slot_len = float(pat["slot_length_mm"])
    slot_w = float(pat["slot_width_mm"])

    y_center = pat.get("y_center_mm", "CENTER")
    y0 = float(y_center) if isinstance(y_center, (int, float)) else (w / 2.0)

    z0 = float(pat.get("z_from_outer_bottom_mm", 0.0))

    centers: list[App.Vector] = []
    x = end_margin
    while x <= (L - end_margin + 1e-6):
        centers.append(App.Vector(x, y0, z0))
        x += pitch

    return centers

    def make_slot_at(x_center: float) -> Part.Shape:
        slot = Part.makeBox(slot_len, slot_w, dz + 2 * eps)
        slot.Placement = App.Placement(
            App.Vector(x_center - slot_len / 2.0, y0 - slot_w / 2.0, z0 - eps),
            App.Rotation()
        )
        return slot

    centers = []
    x = end_margin
    while x <= (L - end_margin + 1e-6):
        centers.append(x)
        x += pitch

    if not centers:
        return solid

    cutters = [make_slot_at(xc) for xc in centers]
    compound = Part.makeCompound(cutters)

    # One boolean cut (fast + stable)
    return solid.cut(compound)

def nearest_slot_center(slot_centers, point: App.Vector):
    if not slot_centers:
        return None
    if point is None:
        return None
    return min(slot_centers, key=lambda v: (v.sub(point)).Length)

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

        mouth = spec.get("mouth_opening") or {}
        lip_depth = spec.get("lip_depth") or {}
        mouth_mm = mouth.get("mm")
        lip_depth_mm = lip_depth.get("mm")

        solid = build_u_channel_lipped(
            width_mm=w,
            depth_mm=h,
            t_mm=t_mm,
            lip_mm=lip_mm,
            length_mm=length_mm,
            mouth_opening_mm=float(mouth_mm) if mouth_mm is not None else None,
            lip_depth_mm=float(lip_depth_mm) if lip_depth_mm is not None else None,
        )

        # --- Piercing / slots (MVP): apply after builder returns solid
        piercing = geom.get("piercing") or {}
        series = piercing.get("series")
        if series:
            spec = resolve_piercing_spec(profile)
            solid = apply_hole_series(
                solid,
                spec,
                length_mm,
                width_mm=w,
                thickness_mm=t_mm,
        )

        return solid

    # -------------------------------------------------
    # FALLBACK: existing crude U-channel logic
    # -------------------------------------------------
    outer = _rect_profile_yz(w, h)
    inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
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

    # --- Piercing / slots (MVP)
    piercing = geom.get("piercing") or {}
    series = piercing.get("series")
    if series:
        spec = resolve_piercing_spec(profile)
        solid = apply_hole_series(
            solid,
            spec,
            length_mm,
            width_mm=w,
            thickness_mm=t_mm,
    )

    return solid

def build_u_channel_lipped(
    width_mm: float,
    depth_mm: float,
    t_mm: float,
    lip_mm: float,
    length_mm: float,
    mouth_opening_mm: float | None = None,
    lip_depth_mm: float | None = None,
) -> Part.Shape:
    """
    Lipped U-channel, extruded along +X.

    Stable checkpoint geometry:
    - published mouth opening remains the clear throat
    - lip_depth is vertical
    - section is represented as a union of simple rectangular solids only
    - no arcs, no self-intersecting face wires, no tangent booleans

    This is intentionally a topology-safe test geometry so the GUI and smoke
    diagnostics work again before rounded curls are reintroduced.
    """
    w = float(width_mm)
    h = float(depth_mm)
    t = max(float(t_mm), 0.1)
    lip = max(float(lip_mm), 0.0)
    L = float(length_mm)

    def legacy_rectangular() -> Part.Shape:
        web = Part.makeBox(L, w, t)
        left_wall = Part.makeBox(L, t, max(h - t, 0.1))
        left_wall.Placement = App.Placement(App.Vector(0, 0, t), App.Rotation())
        right_wall = Part.makeBox(L, t, max(h - t, 0.1))
        right_wall.Placement = App.Placement(App.Vector(0, w - t, t), App.Rotation())
        solid = web.fuse(left_wall).fuse(right_wall)

        if lip > 0:
            max_lip = max((w - 2*t)/2.0 - 0.1, 0.0)
            lip_eff = min(lip, max_lip)
            left_lip = Part.makeBox(L, lip_eff, t)
            left_lip.Placement = App.Placement(App.Vector(0, t, h - t), App.Rotation())
            right_lip = Part.makeBox(L, lip_eff, t)
            right_lip.Placement = App.Placement(App.Vector(0, w - t - lip_eff, h - t), App.Rotation())
            solid = solid.fuse(left_lip).fuse(right_lip)

        return solid.removeSplitter()

    if mouth_opening_mm is None or lip_depth_mm is None:
        return legacy_rectangular()

    opening = float(mouth_opening_mm)
    lip_depth = float(lip_depth_mm)
    if not (0.0 < opening < w):
        raise ValueError("invalid lipped-channel geometry: require 0 < mouth_opening < width")
    if lip_depth <= 0.0:
        raise ValueError("invalid lipped-channel geometry: lip depth must be positive")

    side = (w - opening) / 2.0
    if side < t:
        raise ValueError("mouth opening leaves insufficient shoulder width")

    # Build the channel from overlapping rectangular prisms.  Overlap by a
    # small epsilon at joins so OCC sees volumetric intersections rather than
    # zero-area/tangent contacts.
    eps = min(0.05, t * 0.05)

    web = Part.makeBox(L, w, t)

    left_wall = Part.makeBox(L, t, h - t + eps)
    left_wall.Placement = App.Placement(App.Vector(0, 0, t - eps), App.Rotation())

    right_wall = Part.makeBox(L, t, h - t + eps)
    right_wall.Placement = App.Placement(App.Vector(0, w - t, t - eps), App.Rotation())

    shoulder_len = side - t + eps
    left_shoulder = Part.makeBox(L, shoulder_len, t)
    left_shoulder.Placement = App.Placement(App.Vector(0, t - eps, h - t), App.Rotation())

    right_shoulder = Part.makeBox(L, shoulder_len, t)
    right_shoulder.Placement = App.Placement(
        App.Vector(0, w - side, h - t), App.Rotation()
    )

    lip_len = min(lip_depth, h - t)
    left_return = Part.makeBox(L, t, lip_len + eps)
    left_return.Placement = App.Placement(
        App.Vector(0, side - eps, h - lip_len), App.Rotation()
    )

    right_return = Part.makeBox(L, t, lip_len + eps)
    right_return.Placement = App.Placement(
        App.Vector(0, w - side, h - lip_len), App.Rotation()
    )

    solid = web
    for piece in (
        left_wall, right_wall,
        left_shoulder, right_shoulder,
        left_return, right_return,
    ):
        solid = solid.fuse(piece)

    solid = solid.removeSplitter()

    if solid.isNull() or not solid.isValid():
        raise RuntimeError("lipped-channel extrusion produced invalid solid")

    if getattr(solid, "Solids", None) and len(solid.Solids) == 1:
        solid = solid.Solids[0]

    return solid

