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
    """Rectangle in the YZ plane (X=0). w -> Y extent, h -> Z extent."""
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

    outer = _rect_profile_yz(w, h)
    inner = _rect_profile_yz(max(w - 2 * t, 0.1), max(h - t, 0.1))
    inner.translate(App.Vector(0, t, t))
    face = outer.cut(inner)

    solid = face.extrude(App.Vector(length_mm, 0, 0))

    if mode == "detailed":
        lip_w = min(6.0, w * 0.2)
        lip_t = min(2.0, t)

        left = Part.makeBox(length_mm, lip_w, lip_t)
        left.Placement = App.Placement(App.Vector(0, 0, h - lip_t), App.Rotation())

        right = Part.makeBox(length_mm, lip_w, lip_t)
        right.Placement = App.Placement(App.Vector(0, w - lip_w, h - lip_t), App.Rotation())

        solid = solid.fuse(left).fuse(right)

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
    """Stable topology-safe checkpoint geometry for lipped U-channel."""
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
    right_shoulder.Placement = App.Placement(App.Vector(0, w - side, h - t), App.Rotation())

    lip_len = min(lip_depth, h - t)
    left_return = Part.makeBox(L, t, lip_len + eps)
    left_return.Placement = App.Placement(App.Vector(0, side - eps, h - lip_len), App.Rotation())
    right_return = Part.makeBox(L, t, lip_len + eps)
    right_return.Placement = App.Placement(App.Vector(0, w - side, h - lip_len), App.Rotation())

    solid = web
    for piece in (left_wall, right_wall, left_shoulder, right_shoulder, left_return, right_return):
        solid = solid.fuse(piece)
    solid = solid.removeSplitter()
    if solid.isNull() or not solid.isValid():
        raise RuntimeError("lipped-channel extrusion produced invalid solid")
    if getattr(solid, "Solids", None) and len(solid.Solids) == 1:
        solid = solid.Solids[0]
    return solid


def build_u_channel_lipped_experimental(
    width_mm: float,
    depth_mm: float,
    t_mm: float,
    length_mm: float,
    mouth_opening_mm: float,
    lip_depth_mm: float,
    bend_radius_mm: float | None = None,
    lower_bend_radius_mm: float | None = None,
) -> Part.Shape:
    """Experimental upper-shoulder bends using a centerline-style decomposition.

    Production geometry is untouched.  This version avoids one hand-walked
    perimeter.  It constructs each shoulder bend as a quarter-annular prism and
    joins it to simple web/shoulder/return prisms with small volumetric overlaps.
    """
    w = float(width_mm)
    h = float(depth_mm)
    t = max(float(t_mm), 0.1)
    L = float(length_mm)
    opening = float(mouth_opening_mm)
    lip_depth = float(lip_depth_mm)
    side = (w - opening) / 2.0
    r_i = float(bend_radius_mm) if bend_radius_mm is not None else t
    r_i = max(r_i, 0.1)
    r_o = r_i + t
    lower_ri = float(lower_bend_radius_mm) if lower_bend_radius_mm is not None else 0.0
    if lower_ri < 0.0:
        raise ValueError("lower bend radius cannot be negative")
    lower_ro = lower_ri + t

    if not (0.0 < opening < w):
        raise ValueError("invalid experimental channel opening")
    if side <= r_o:
        raise ValueError("experimental shoulder bend does not fit side projection")
    if lip_depth <= 0.0:
        raise ValueError("experimental lip depth must be positive")

    eps = min(0.05, t * 0.05)

    # The lower-corner radius is independent of the upper shoulder radius.
    # With lower_ri=0 the earlier square-corner checkpoint is reproduced.
    web_width = w if lower_ri == 0.0 else w - 2.0 * lower_ro + 2.0 * eps
    if web_width <= 0.0:
        raise ValueError("lower bends leave no straight web")
    web = Part.makeBox(L, web_width, t)
    if lower_ri > 0.0:
        web.Placement = App.Placement(App.Vector(0, lower_ro-eps, 0), App.Rotation())
    wall_z0 = t - eps if lower_ri == 0.0 else lower_ro - eps
    wall_h = h - r_o - wall_z0
    if wall_h <= 0.0:
        raise ValueError("experimental shoulder bend leaves no straight wall")

    left_wall = Part.makeBox(L, t, wall_h)
    left_wall.Placement = App.Placement(App.Vector(0, 0, wall_z0), App.Rotation())
    right_wall = Part.makeBox(L, t, wall_h)
    right_wall.Placement = App.Placement(App.Vector(0, w - t, wall_z0), App.Rotation())

    # Build a quarter-annulus face in YZ and extrude it along X.
    def quarter_annulus(center_y: float, center_z: float, quadrant: str) -> Part.Shape:
        if quadrant == "left":
            outer = Part.Arc(
                App.Vector(0, center_y-r_o, center_z),
                App.Vector(0, center_y-r_o*0.7071067811865476, center_z+r_o*0.7071067811865476),
                App.Vector(0, center_y, center_z+r_o),
            ).toShape()
            cap_top = Part.makeLine(
                App.Vector(0, center_y, center_z+r_o),
                App.Vector(0, center_y, center_z+r_i),
            )
            inner = Part.Arc(
                App.Vector(0, center_y, center_z+r_i),
                App.Vector(0, center_y-r_i*0.7071067811865476, center_z+r_i*0.7071067811865476),
                App.Vector(0, center_y-r_i, center_z),
            ).toShape()
            cap_side = Part.makeLine(
                App.Vector(0, center_y-r_i, center_z),
                App.Vector(0, center_y-r_o, center_z),
            )
        else:
            outer = Part.Arc(
                App.Vector(0, center_y+r_o, center_z),
                App.Vector(0, center_y+r_o*0.7071067811865476, center_z+r_o*0.7071067811865476),
                App.Vector(0, center_y, center_z+r_o),
            ).toShape()
            cap_top = Part.makeLine(
                App.Vector(0, center_y, center_z+r_o),
                App.Vector(0, center_y, center_z+r_i),
            )
            inner = Part.Arc(
                App.Vector(0, center_y, center_z+r_i),
                App.Vector(0, center_y+r_i*0.7071067811865476, center_z+r_i*0.7071067811865476),
                App.Vector(0, center_y+r_i, center_z),
            ).toShape()
            cap_side = Part.makeLine(
                App.Vector(0, center_y+r_i, center_z),
                App.Vector(0, center_y+r_o, center_z),
            )

        wire = Part.Wire([outer, cap_top, inner, cap_side])
        face = Part.Face(wire)
        if face.isNull() or not face.isValid():
            raise RuntimeError("experimental quarter-annulus face is invalid")
        return face.extrude(App.Vector(L, 0, 0))

    left_center_y = r_o
    right_center_y = w - r_o
    center_z = h - r_o

    left_bend = quarter_annulus(left_center_y, center_z, "left")
    right_bend = quarter_annulus(right_center_y, center_z, "right")

    # Lower convex 90-degree transitions: concentric radii with constant t.
    # Use explicit annular sectors; the upper corner primitive is unchanged.
    lower_bends = []
    if lower_ri > 0.0:
        k = 0.7071067811865476
        for cy, sign in ((lower_ro, -1.0), (w-lower_ro, 1.0)):
            cz = lower_ro
            outer = Part.Arc(
                App.Vector(0, cy, 0),
                App.Vector(0, cy+sign*lower_ro*k, cz-lower_ro*k),
                App.Vector(0, cy+sign*lower_ro, cz),
            ).toShape()
            cap_wall = Part.makeLine(
                App.Vector(0, cy+sign*lower_ro, cz),
                App.Vector(0, cy+sign*lower_ri, cz),
            )
            inner = Part.Arc(
                App.Vector(0, cy+sign*lower_ri, cz),
                App.Vector(0, cy+sign*lower_ri*k, cz-lower_ri*k),
                App.Vector(0, cy, cz-lower_ri),
            ).toShape()
            cap_web = Part.makeLine(
                App.Vector(0, cy, cz-lower_ri),
                App.Vector(0, cy, 0),
            )
            sector = Part.Face(Part.Wire([outer, cap_wall, inner, cap_web]))
            if sector.isNull() or not sector.isValid():
                raise RuntimeError("experimental lower-bend face is invalid")
            lower_bends.append(sector.extrude(App.Vector(L, 0, 0)))

    # Horizontal shoulders begin just past the bends and terminate at the
    # published mouth edges.  Returns remain square and vertical for now.
    left_shoulder_start = r_o
    left_shoulder_end = side
    shoulder_len = left_shoulder_end - left_shoulder_start + eps
    if shoulder_len <= 0.0:
        raise ValueError("experimental shoulder bend consumes full side projection")

    left_shoulder = Part.makeBox(L, shoulder_len, t)
    left_shoulder.Placement = App.Placement(
        App.Vector(0, left_shoulder_start-eps, h-t), App.Rotation()
    )
    right_shoulder = Part.makeBox(L, shoulder_len, t)
    right_shoulder.Placement = App.Placement(
        App.Vector(0, w-side, h-t), App.Rotation()
    )

    lip_len = min(lip_depth, h-t)
    left_return = Part.makeBox(L, t, lip_len+eps)
    left_return.Placement = App.Placement(
        App.Vector(0, side-eps, h-lip_len), App.Rotation()
    )
    right_return = Part.makeBox(L, t, lip_len+eps)
    right_return.Placement = App.Placement(
        App.Vector(0, w-side, h-lip_len), App.Rotation()
    )

    solid = web
    for piece in (
        left_wall, right_wall,
        *lower_bends,
        left_bend, right_bend,
        left_shoulder, right_shoulder,
        left_return, right_return,
    ):
        solid = solid.fuse(piece)

    solid = solid.removeSplitter()
    if solid.isNull() or not solid.isValid():
        raise RuntimeError("experimental shoulder-bend solid is invalid")
    if getattr(solid, "Solids", None) and len(solid.Solids) == 1:
        solid = solid.Solids[0]
    return solid
