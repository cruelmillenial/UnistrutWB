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
        gap = spec.get("lip_tip_gap") or {}
        mouth_mm = mouth.get("mm")
        gap_mm = gap.get("mm")

        solid = build_u_channel_lipped(
            width_mm=w,
            depth_mm=h,
            t_mm=t_mm,
            lip_mm=lip_mm,
            length_mm=length_mm,
            mouth_opening_mm=float(mouth_mm) if mouth_mm is not None else None,
            lip_tip_gap_mm=float(gap_mm) if gap_mm is not None else None,
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
    lip_tip_gap_mm: float | None = None,
) -> Part.Shape:
    """
    Lipped U-channel, extruded along +X.

    Rich-geometry path:
    - derive lip curl radius from mouth opening and tip gap
    - construct one closed 2D material boundary in the YZ plane
    - make a single Part.Face
    - extrude that face along +X

    The lip radius remains an explicit modeling hypothesis derived from the
    ETL contract, not manufacturer-specified bend-radius data.

    Profiles without mouth/tip dimensions keep the legacy rectangular-return
    fallback so partially upgraded catalog entries remain usable.
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
        left.Placement = App.Placement(
            App.Vector(0, t, h - t),
            App.Rotation(),
        )
        right = Part.makeBox(L, lip_eff, t)
        right.Placement = App.Placement(
            App.Vector(0, w - t - lip_eff, h - t),
            App.Rotation(),
        )
        return solid.fuse(left).fuse(right)

    if mouth_opening_mm is None or lip_tip_gap_mm is None:
        return legacy_rectangular()

    opening = float(mouth_opening_mm)
    gap = float(lip_tip_gap_mm)
    if not (0.0 < gap < opening < w):
        raise ValueError(
            "invalid lipped-channel geometry: require 0 < lip_tip_gap < "
            "mouth_opening < width"
        )

    side_projection = (w - opening) / 2.0
    tip_projection = (opening - gap) / 2.0
    r_mid = tip_projection / 2.0

    if r_mid <= t / 2.0:
        raise ValueError(
            "derived lip radius is too small for requested material thickness"
        )

    r_in = r_mid - t / 2.0
    r_out = r_mid + t / 2.0

    # Outer material boundary follows the overall envelope.
    y_lo = 0.0
    y_hi = w
    z_lo = 0.0
    z_hi = h

    # Approximate tangent locations for the curled return, symmetric about the
    # channel centerline. The mouth datum sets the curl shoulder; the tip-gap
    # datum sets the inner-most lip tips.
    y_left_mouth = side_projection
    y_right_mouth = w - side_projection
    y_left_tip_mid = (w - gap) / 2.0
    y_right_tip_mid = (w + gap) / 2.0

    # Curl center positions are derived so the centerline arc spans 180 deg
    # from the top shoulder to the inward/downward tip.
    c_left_y = y_left_mouth + r_mid
    c_right_y = y_right_mouth - r_mid
    c_z = z_hi - r_mid

    # Build the boundary explicitly. Start at lower-left outer corner and walk
    # counter-clockwise around the material, including outer curl surfaces,
    # then return along the inner surfaces.
    edges = []

    def line(y1, z1, y2, z2):
        edges.append(
            Part.makeLine(
                App.Vector(0, y1, z1),
                App.Vector(0, y2, z2),
            )
        )

    def arc3(y1, z1, ym, zm, y2, z2):
        edges.append(
            Part.Arc(
                App.Vector(0, y1, z1),
                App.Vector(0, ym, zm),
                App.Vector(0, y2, z2),
            ).toShape()
        )

    # ---- outer boundary
    line(y_lo, z_lo, y_hi, z_lo)
    line(y_hi, z_lo, y_hi, z_hi)
    line(y_hi, z_hi, c_right_y, z_hi)

    # Right outer semicircle: top shoulder -> inward/downward outer tip.
    arc3(
        c_right_y, z_hi,
        c_right_y - r_out / 1.41421356237, c_z + r_out / 1.41421356237,
        c_right_y - r_out, c_z,
    )

    # Bridge outer tip to inner tip at the free edge.
    line(c_right_y - r_out, c_z, c_right_y - r_in, c_z)

    # Right inner semicircle back to the inner shoulder.
    arc3(
        c_right_y - r_in, c_z,
        c_right_y - r_in / 1.41421356237, c_z + r_in / 1.41421356237,
        c_right_y, c_z + r_in,
    )

    # Inner right wall down to inside-bottom.
    line(c_right_y, c_z + r_in, w - t, z_hi - t)
    line(w - t, z_hi - t, w - t, t)
    line(w - t, t, t, t)
    line(t, t, t, z_hi - t)

    # Inner left shoulder to left inner curl.
    line(t, z_hi - t, c_left_y, c_z + r_in)

    # Left inner semicircle: inner shoulder -> inward/downward tip.
    arc3(
        c_left_y, c_z + r_in,
        c_left_y + r_in / 1.41421356237, c_z + r_in / 1.41421356237,
        c_left_y + r_in, c_z,
    )

    # Bridge inner tip to outer tip at free edge.
    line(c_left_y + r_in, c_z, c_left_y + r_out, c_z)

    # Left outer semicircle back to outer top shoulder.
    arc3(
        c_left_y + r_out, c_z,
        c_left_y + r_out / 1.41421356237, c_z + r_out / 1.41421356237,
        c_left_y, z_hi,
    )

    line(c_left_y, z_hi, y_lo, z_hi)
    line(y_lo, z_hi, y_lo, z_lo)

    wire = Part.Wire(edges)
    if not wire.isClosed():
        raise RuntimeError("lipped-channel cross-section wire is not closed")

    face = Part.Face(wire)
    if face.isNull() or not face.isValid():
        raise RuntimeError("lipped-channel cross-section face is invalid")

    solid = face.extrude(App.Vector(L, 0, 0))
    if solid.isNull() or not solid.isValid():
        raise RuntimeError("lipped-channel extrusion produced invalid solid")
    return solid

