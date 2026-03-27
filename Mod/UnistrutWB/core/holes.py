import Part
import FreeCAD as App
import json
from pathlib import Path

_HOLE_MAP_CACHE = None

def _data_dir() -> Path:
    here = Path(__file__).resolve()
    return (here.parent.parent / "data").resolve()

def load_hole_series_map():
    global _HOLE_MAP_CACHE
    if _HOLE_MAP_CACHE is not None:
        return _HOLE_MAP_CACHE

    p = _data_dir() / "mapping_hole_series.json"
    if not p.exists():
        _HOLE_MAP_CACHE = {}
        return _HOLE_MAP_CACHE

    with p.open("r", encoding="utf-8") as f:
        _HOLE_MAP_CACHE = json.load(f)

    return _HOLE_MAP_CACHE

def get_series_spec(series_code: str) -> dict:
    m = load_hole_series_map()
    return ((m.get("hole_series") or {}).get(series_code, {}) or {}).copy()

def get_template_spec(template_name) -> dict:
    if not template_name:
        return {}
    m = load_hole_series_map()
    return ((m.get("templates") or {}).get(template_name, {}) or {}).copy()

def resolve_piercing_spec(profile: dict, overrides: dict | None = None) -> dict:
    geom = profile.get("geometry") or {}
    piercing = geom.get("piercing") or {}

    series_code = piercing.get("series")
    template_name = piercing.get("template")
    profile_overrides = (piercing.get("overrides") or {}).copy()

    spec = {}
    if series_code:
        spec.update(get_series_spec(series_code))

    spec.update(get_template_spec(template_name))
    spec.update(profile_overrides)

    if overrides:
        spec.update(overrides)

    if series_code and "series" not in spec:
        spec["series"] = series_code

    return spec

def apply_hole_series(
    solid,
    series,
    length_mm,
    *,
    width_mm=41.3,
    thickness_mm=1.9,
):
    """
    Apply a simple web slot series to a channel.

    Coordinate convention:
    - X = channel length
    - Y = channel width
    - Z = channel height

    This cuts slots through the web thickness (+Z), centered across width (Y).
    """

    pat = series.get("slot_pattern", series)

    pitch = float(pat["pitch_mm"])
    offset = float(pat.get("offset_mm", pat.get("end_margin_mm", pitch / 2.0)))

    slot_len = float(pat.get("slot_length_mm", pat.get("diameter_mm", 14.0)))
    slot_w = float(pat.get("slot_width_mm", pat.get("diameter_mm", 14.0)))

    y_center_raw = pat.get("y_center_mm", width_mm / 2.0)
    y_center = width_mm / 2.0 if y_center_raw == "CENTER" else float(y_center_raw)

    eps = 0.05
    slots = []

    x = offset
    while x <= (length_mm - offset + 1e-6):
        slot = Part.makeBox(
            slot_len,
            slot_w,
            thickness_mm + 2 * eps,
        )
        slot.Placement = App.Placement(
            App.Vector(
                x - slot_len / 2.0,
                y_center - slot_w / 2.0,
                -eps,
            ),
            App.Rotation(),
        )
        slots.append(slot)
        x += pitch

    if not slots:
        return solid

    tool = Part.makeCompound(slots)
    return solid.cut(tool)

def compute_slot_centers(series, length_mm, *, width_mm=41.3):
    """
    Return list of (x, y, z) slot centers using the same spec as cutting.
    Z is on the web mid-plane (0), since cutting spans thickness.
    """
    pat = series.get("slot_pattern", series)

    pitch = float(pat["pitch_mm"])
    offset = float(pat.get("offset_mm", pat.get("end_margin_mm", pitch / 2.0)))

    y_center_raw = pat.get("y_center_mm", width_mm / 2.0)
    y_center = width_mm / 2.0 if y_center_raw == "CENTER" else float(y_center_raw)

    centers = []
    x = offset
    while x <= (length_mm - offset + 1e-6):
        centers.append((x, y_center, 0.0))
        x += pitch

    return centers