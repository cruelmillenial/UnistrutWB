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

    When mouth_opening_mm and lip_tip_gap_mm are present, build a continuous
    2D sheet-metal section from line segments plus tangent arcs. The lip radius
    is still the ETL model hypothesis:

        side_projection = (width - mouth_opening) / 2
        tip_projection = (mouth_opening - lip_tip_gap) / 2
        r_mid = tip_projection / 2

    The section is generated from a midline path and offset by +/- t/2 to make
    a continuous wall-thickness envelope. This avoids free-standing annuli and
    keeps the lip connected to the sidewall.

    Profiles without the richer mouth/gap inputs retain the legacy rectangular
    return fallback.
    """
    w = float(width_mm)
    h = float(depth_mm)
    t = max(float(t_mm), 0.1)
    lip = max(float(lip_mm), 0.0)
    L = float(length_mm)

    if lip <= 0:
        outer = _rect_profile_yz(w, h)
        inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
        inner.translate(App.Vector(0, t, t))
        return outer.cut(inner).extrude(App.Vector(L, 0, 0))

    if mouth_opening_mm is not None and lip_tip_gap_mm is not None:
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

        # Midline geometry in YZ plane.
        y_left = t / 2.0
        y_right = w - t / 2.0
        z_bottom = t / 2.0
        z_top = h - t / 2.0

        # Horizontal projection from each wall to the nominal mouth datum.
        shelf = max(side_projection - t / 2.0, 0.0)

        # Curl center locations. Each lip curls inward and downward through 180 deg.
        c_left_y = y_left + shelf + r_mid
        c_right_y = y_right - shelf - r_mid
        c_z = z_top - r_mid

        # Centerline path: left lip tip -> left curl -> left wall -> bottom ->
        # right wall -> right curl -> right lip tip.
        p0 = App.Vector(0, c_left_y + r_mid, c_z)  # left tip
        p1 = App.Vector(0, c_left_y, c_z + r_mid)  # left curl top
        p2 = App.Vector(0, y_left, z_top)           # left wall top
        p3 = App.Vector(0, y_left, z_bottom)
        p4 = App.Vector(0, y_right, z_bottom)
        p5 = App.Vector(0, y_right, z_top)          # right wall top
        p6 = App.Vector(0, c_right_y, c_z + r_mid) # right curl top
        p7 = App.Vector(0, c_right_y - r_mid, c_z) # right tip

        # Build centerline as ordered edges.
        edges = [
            Part.Arc(p0, App.Vector(0, c_left_y + r_mid / 1.41421356237, c_z + r_mid / 1.41421356237), p1).toShape(),
            Part.makeLine(p1, p2),
            Part.makeLine(p2, p3),
            Part.makeLine(p3, p4),
            Part.makeLine(p4, p5),
            Part.makeLine(p5, p6),
            Part.Arc(p6, App.Vector(0, c_right_y - r_mid / 1.41421356237, c_z + r_mid / 1.41421356237), p7).toShape(),
        ]
        center_wire = Part.Wire(edges)

        # Sweep a rectangular section of thickness t along the centerline.
        # FreeCAD's pipe keeps the material continuous through the bends and
        # gives us a single connected sheet-metal solid.
        seed = Part.makePlane(
            t,
            L,
            App.Vector(0, p0.y - t / 2.0, p0.z - L / 2.0),
            App.Vector(1, 0, 0),
        )
        # The generic pipe API is sensitive to profile orientation; if this
        # fails in a given OCC build, raise clearly rather than returning
        # disconnected geometry.
        try:
            section = center_wire.makePipeShell([Part.Wire(seed.Edges)], True, False)
        except Exception as exc:
            raise RuntimeError("continuous lipped-channel sweep failed") from exc

        return section

    # Legacy fallback: outer-minus-inner U plus rectangular top returns.
    outer = _rect_profile_yz(w, h)
    inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
    inner.translate(App.Vector(0, t, t))
    face = outer.cut(inner)
    solid = face.extrude(App.Vector(L, 0, 0))

    max_lip = max((w - 2 * t) / 2.0 - 0.1, 0.0)
    lip = min(lip, max_lip)

    left = Part.makeBox(L, lip, t)
    left.Placement = App.Placement(
        App.Vector(0, t, h - t),
        App.Rotation(),
    )
    right = Part.makeBox(L, lip, t)
    right.Placement = App.Placement(
        App.Vector(0, w - t - lip, h - t),
        App.Rotation(),
    )
    return solid.fuse(left).fuse(right)

