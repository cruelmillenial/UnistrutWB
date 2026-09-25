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

    Rich geometry keeps the published mouth opening as the clear throat and
    interprets lip_depth as a vertical terminal-curl dimension.  The section is
    built from robust fused solids rather than one self-intersecting boundary
    wire, because OCC can reject otherwise-closed wires with overlapping curl
    edges.
    """
    w = float(width_mm)
    h = float(depth_mm)
    t = max(float(t_mm), 0.1)
    lip = max(float(lip_mm), 0.0)
    L = float(length_mm)

    def legacy_rectangular() -> Part.Shape:
        outer = _rect_profile_yz(w, h)
        inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
        inner.translate(App.Vector(0, t, t))
        face = outer.cut(inner)
        solid = face.extrude(App.Vector(L, 0, 0))

        if lip <= 0:
            return solid

        max_lip = max((w - 2 * t) / 2.0 - 0.1, 0.0)
        lip_eff = min(lip, max_lip)
        left = Part.makeBox(L, lip_eff, t)
        left.Placement = App.Placement(App.Vector(0, t, h - t), App.Rotation())
        right = Part.makeBox(L, lip_eff, t)
        right.Placement = App.Placement(App.Vector(0, w - t - lip_eff, h - t), App.Rotation())
        return solid.fuse(left).fuse(right)

    if mouth_opening_mm is None or lip_depth_mm is None:
        return legacy_rectangular()

    opening = float(mouth_opening_mm)
    lip_depth = float(lip_depth_mm)
    if not (0.0 < opening < w):
        raise ValueError("invalid lipped-channel geometry: require 0 < mouth_opening < width")
    if lip_depth <= t:
        raise ValueError("invalid lipped-channel geometry: lip depth must exceed thickness")

    side_projection = (w - opening) / 2.0

    # Base U shell, open at the top.
    outer = _rect_profile_yz(w, h)
    inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
    inner.translate(App.Vector(0, t, t))
    base_face = outer.cut(inner)
    solid = base_face.extrude(App.Vector(L, 0, 0))

    # Add the horizontal shoulders up to the mouth edges.
    left_shoulder = Part.makeBox(L, max(side_projection - t, 0.0), t)
    left_shoulder.Placement = App.Placement(App.Vector(0, t, h - t), App.Rotation())
    right_shoulder = Part.makeBox(L, max(side_projection - t, 0.0), t)
    right_shoulder.Placement = App.Placement(
        App.Vector(0, w - side_projection, h - t), App.Rotation()
    )
    solid = solid.fuse(left_shoulder).fuse(right_shoulder)

    # Terminal curls: annular half-cylinders in the YZ section, extruded along X.
    # Treat lip_depth as the outside diameter of the curl.  Keep the published
    # mouth opening untouched: each curl develops downward from its mouth edge.
    r_out = lip_depth / 2.0
    r_in = r_out - t
    if r_in <= 0.0:
        raise ValueError("lip depth is too small for requested material thickness")

    zc = h - r_out
    y_left = side_projection
    y_right = w - side_projection

    def half_annulus(cy: float, inward_sign: float) -> Part.Shape:
        # Build a 2D half-annulus in YZ and extrude it.  The diameter lies on
        # the vertical line y=cy; the arc bulges inward into the channel.
        yo = cy + inward_sign * r_out
        yi = cy + inward_sign * r_in
        edges = [
            Part.Arc(
                App.Vector(0, cy, h),
                App.Vector(0, yo, zc),
                App.Vector(0, cy, h - 2.0 * r_out),
            ).toShape(),
            Part.makeLine(
                App.Vector(0, cy, h - 2.0 * r_out),
                App.Vector(0, cy, h - 2.0 * r_in),
            ),
            Part.Arc(
                App.Vector(0, cy, h - 2.0 * r_in),
                App.Vector(0, yi, zc),
                App.Vector(0, cy, h),
            ).toShape(),
        ]
        wire = Part.Wire(edges)
        face = Part.Face(wire)
        return face.extrude(App.Vector(L, 0, 0))

    left_curl = half_annulus(y_left, +1.0)
    right_curl = half_annulus(y_right, -1.0)
    solid = solid.fuse(left_curl).fuse(right_curl)

    if solid.isNull() or not solid.isValid():
        raise RuntimeError("lipped-channel extrusion produced invalid solid")

    # Normalize boolean result into a single solid where possible.
    if getattr(solid, "Solids", None) and len(solid.Solids) == 1:
        solid = solid.Solids[0]

    return solid

