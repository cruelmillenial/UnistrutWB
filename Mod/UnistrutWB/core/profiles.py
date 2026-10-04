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

def _compute_slot_centers_web(*, length_mm: float, width_mm: float, thickness_mm: float, series_code: str) -> list[App.Vector]:
    m = _load_hole_series_map()
    hs = (m.get("hole_series") or {}).get(series_code) or {}
    pat = hs.get("slot_pattern")
    if not pat:
        return []
    L = float(length_mm)
    w = float(width_mm)
    pitch = float(pat["pitch_mm"])
    end_margin = float(pat.get("end_margin_mm", pitch / 2.0))
    y_center = pat.get("y_center_mm", "CENTER")
    y0 = float(y_center) if isinstance(y_center, (int, float)) else (w / 2.0)
    z0 = float(pat.get("z_from_outer_bottom_mm", 0.0))
    centers: list[App.Vector] = []
    x = end_margin
    while x <= (L - end_margin + 1e-6):
        centers.append(App.Vector(x, y0, z0))
        x += pitch
    return centers

def nearest_slot_center(slot_centers, point: App.Vector):
    if not slot_centers or point is None:
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
            solid = apply_hole_series(solid, spec, length_mm, width_mm=w, thickness_mm=t_mm)
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
        solid = apply_hole_series(solid, spec, length_mm, width_mm=w, thickness_mm=t_mm)
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
    """Topology-safe production checkpoint geometry."""
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
) -> Part.Shape:
    """Experimental single-face section with rounded upper shoulders only.

    Production geometry remains untouched. The lower web corners and terminal
    returns stay square. The only new physical feature is one shared inside
    radius for the two 90-degree transitions from sidewall to inward shoulder.
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

    if not (0.0 < opening < w):
        raise ValueError("invalid experimental channel opening")
    if side <= r_o:
        raise ValueError("experimental shoulder bend does not fit side projection")
    if lip_depth <= 0.0:
        raise ValueError("experimental lip depth must be positive")

    y_l = side
    y_r = w - side
    z_tip = h - min(lip_depth, h - t)

    # Keep the overall envelope at exactly H. Each outside shoulder is a
    # quarter-circle tangent to the outer wall and top shoulder; its matching
    # inside arc is offset by material thickness.
    edges = []
    def line(y1, z1, y2, z2):
        if abs(y2-y1) < 1e-9 and abs(z2-z1) < 1e-9:
            return
        edges.append(Part.makeLine(App.Vector(0,y1,z1), App.Vector(0,y2,z2)))
    def arc(y1,z1,ym,zm,y2,z2):
        edges.append(Part.Arc(App.Vector(0,y1,z1), App.Vector(0,ym,zm), App.Vector(0,y2,z2)).toShape())

    k = 0.7071067811865476

    # Outer boundary, clockwise from lower-left.
    line(0,0,w,0)
    line(w,0,w,h-r_o)
    c_ry = w-r_o
    c_rz = h-r_o
    arc(w,h-r_o, c_ry+r_o*k,c_rz+r_o*k, w-r_o,h)
    line(w-r_o,h,y_r,h)
    line(y_r,h,y_r,z_tip)
    line(y_r,z_tip,y_r-t,z_tip)
    line(y_r-t,z_tip,y_r-t,h-t)

    # Right inner shoulder arc back to vertical inner wall.
    c_ri_y = w-t-r_i
    c_ri_z = h-t-r_i
    line(y_r-t,h-t,c_ri_y,h-t)
    arc(c_ri_y,h-t, c_ri_y+r_i*k,c_ri_z+r_i*k, w-t,c_ri_z)
    line(w-t,c_ri_z,w-t,t)
    line(w-t,t,t,t)
    line(t,t,t,c_ri_z)

    # Left inner shoulder and return, mirrored.
    c_li_y = t+r_i
    c_li_z = c_ri_z
    arc(t,c_li_z, c_li_y-r_i*k,c_li_z+r_i*k, c_li_y,h-t)
    line(c_li_y,h-t,y_l+t,h-t)
    line(y_l+t,h-t,y_l+t,z_tip)
    line(y_l+t,z_tip,y_l,z_tip)
    line(y_l,z_tip,y_l,h)
    line(y_l,h,r_o,h)

    c_ly = r_o
    c_lz = h-r_o
    arc(r_o,h, c_ly-r_o*k,c_lz+r_o*k, 0,h-r_o)
    line(0,h-r_o,0,0)

    wire = Part.Wire(edges)
    if not wire.isClosed():
        raise RuntimeError("experimental shoulder-bend wire is not closed")
    face = Part.Face(wire)
    if face.isNull() or not face.isValid():
        raise RuntimeError("experimental shoulder-bend face is invalid")
    solid = face.extrude(App.Vector(L,0,0))
    if solid.isNull() or not solid.isValid():
        raise RuntimeError("experimental shoulder-bend extrusion is invalid")
    return solid
