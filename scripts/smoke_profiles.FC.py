from UnistrutWB.core import profiles
from UnistrutWB.core.loader import Catalog
import importlib

importlib.reload(profiles)

cat = Catalog.load(force_reload=True)

for profile_id in ("P1000", "P4100"):
    profile = cat.get_profile(profile_id)
    shape = profiles.build_channel(profile, 1000.0, mode="simple")
    spec = profile["geometry"]["profile_spec"]
    print(profile_id)
    print("  mouth_opening_mm:", spec.get("mouth_opening", {}).get("mm"))
    print("  lip_tip_gap_mm:", spec.get("lip_tip_gap", {}).get("mm"))
    print(
        "  BB:",
        shape.BoundBox.XLength,
        shape.BoundBox.YLength,
        shape.BoundBox.ZLength,
    )
    print("  V:", shape.Volume)
    print("  valid:", shape.isValid())

# Legacy/fallback specimen: no mouth/tip dimensions, so rectangular returns
# remain available for profiles not yet upgraded to the richer contract.
legacy = {
    "geometry": {
        "width": {"mm": 41.275},
        "height": {"mm": 20.6375},
        "thickness": {"mm": 1.905},
        "profile_spec": {
            "kind": "u_channel_lipped",
            "t": {"mm": 1.905},
            "lip_return": {"mm": 9.525},
        },
    }
}
legacy_shape = profiles.build_channel(legacy, 1000.0, mode="simple")
print("legacy fallback valid:", legacy_shape.isValid())

print("\nSECTION VALIDATION")
targets = {
    "P1000": {
        "area_in2": 0.555,
        "centroid_bottom_in": 0.710,
        "centroid_top_in": 0.915,
    },
    "P4100": {
        "area_in2": 0.290,
        "centroid_bottom_in": 0.333,
        "centroid_top_in": 0.480,
    },
}

MM_PER_IN = 25.4
MM2_PER_IN2 = MM_PER_IN ** 2

for profile_id, target in targets.items():
    profile = cat.get_profile(profile_id)
    shape = profiles.build_channel(profile, 1.0, mode="simple")
    area_mm2 = shape.Volume
    area_in2 = area_mm2 / MM2_PER_IN2
    centroid_z_mm = shape.CenterOfMass.z
    centroid_bottom_in = centroid_z_mm / MM_PER_IN
    height_mm = float(profile["geometry"]["height"]["mm"])
    centroid_top_in = (height_mm - centroid_z_mm) / MM_PER_IN
    bb_h = shape.BoundBox.ZLength
    print(profile_id)
    print("  area_in2:", area_in2, "target:", target["area_in2"])
    print("  area_error_pct:", 100.0 * (area_in2 - target["area_in2"]) / target["area_in2"])
    print("  centroid_bottom_in:", centroid_bottom_in, "target:", target["centroid_bottom_in"])
    print("  centroid_top_in:", centroid_top_in, "target:", target["centroid_top_in"])
    print("  nominal_height_mm:", height_mm, "bb_height_mm:", bb_h, "delta_mm:", bb_h - height_mm)

print("\nDIAGNOSTIC DELTAS")
published = {
    "P1000": {"area_in2": 0.555, "centroid_bottom_in": 0.710},
    "P4100": {"area_in2": 0.290, "centroid_bottom_in": 0.333},
}
for profile_id, target in published.items():
    profile = cat.get_profile(profile_id)
    shape = profiles.build_channel(profile, 1.0, mode="simple")
    actual_area_mm2 = shape.Volume
    published_area_mm2 = target["area_in2"] * MM2_PER_IN2
    actual_cz_mm = shape.CenterOfMass.z
    published_cz_mm = target["centroid_bottom_in"] * MM_PER_IN
    print(profile_id)
    print("  published_area_mm2:", published_area_mm2)
    print("  actual_area_mm2:", actual_area_mm2)
    print("  excess_area_mm2:", actual_area_mm2 - published_area_mm2)
    print("  published_centroid_z_mm:", published_cz_mm)
    print("  actual_centroid_z_mm:", actual_cz_mm)
    print("  centroid_delta_mm:", actual_cz_mm - published_cz_mm)
