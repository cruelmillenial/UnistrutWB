import math
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
    print("  lip_depth_mm:", spec.get("lip_depth", {}).get("mm"))
    print("  BB:", shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength)
    print("  V:", shape.Volume)
    print("  valid:", shape.isValid())

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

MM_PER_IN = 25.4
MM2_PER_IN2 = MM_PER_IN ** 2
IN4_TO_MM4 = MM_PER_IN ** 4

fit_targets = {
    "P1000": {"area_in2": 0.555, "centroid_bottom_in": 0.710, "I11_in4": 0.185, "I22_in4": 0.236},
    "P4100": {"area_in2": 0.290, "centroid_bottom_in": 0.333, "I11_in4": 0.026, "I22_in4": 0.107},
}

print("\nCHECKPOINT BASELINE")
for profile_id, target in fit_targets.items():
    profile = cat.get_profile(profile_id)
    shape = profiles.build_channel(profile, 1.0, mode="simple")
    moi = shape.MatrixOfInertia
    print(profile_id)
    print("  valid:", shape.isValid())
    print("  area_in2:", shape.Volume / MM2_PER_IN2, "target:", target["area_in2"])
    print("  centroid_bottom_in:", shape.CenterOfMass.z / MM_PER_IN, "target:", target["centroid_bottom_in"])
    print("  I11_in4:", moi.A22 / IN4_TO_MM4, "target:", target["I11_in4"])
    print("  I22_in4:", moi.A33 / IN4_TO_MM4, "target:", target["I22_in4"])

print("\nEXPERIMENTAL UPPER-SHOULDER BEND")
for profile_id, target in fit_targets.items():
    profile = cat.get_profile(profile_id)
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    t = float(spec["t"]["mm"])
    baseline = profiles.build_channel(profile, 1.0, mode="simple")
    try:
        experimental = profiles.build_u_channel_lipped_experimental(
            width_mm=float(geom["width"]["mm"]),
            depth_mm=float(geom["height"]["mm"]),
            t_mm=t,
            length_mm=1.0,
            mouth_opening_mm=float(spec["mouth_opening"]["mm"]),
            lip_depth_mm=float(spec["lip_depth"]["mm"]),
            bend_radius_mm=t,
        )
    except Exception as exc:
        print(profile_id)
        print("  FAIL:", type(exc).__name__, str(exc))
        continue

    bmoi = baseline.MatrixOfInertia
    emoi = experimental.MatrixOfInertia
    base_area = baseline.Volume / MM2_PER_IN2
    exp_area = experimental.Volume / MM2_PER_IN2
    base_c = baseline.CenterOfMass.z / MM_PER_IN
    exp_c = experimental.CenterOfMass.z / MM_PER_IN
    base_i11 = bmoi.A22 / IN4_TO_MM4
    exp_i11 = emoi.A22 / IN4_TO_MM4
    base_i22 = bmoi.A33 / IN4_TO_MM4
    exp_i22 = emoi.A33 / IN4_TO_MM4

    print(profile_id)
    print("  bend_radius_mm:", t)
    print("  valid:", experimental.isValid())
    print("  BB_height_mm:", experimental.BoundBox.ZLength, "nominal:", float(geom["height"]["mm"]))
    print("  area_in2:", exp_area, "delta_from_baseline:", exp_area - base_area, "target:", target["area_in2"])
    print("  centroid_bottom_in:", exp_c, "delta_from_baseline:", exp_c - base_c, "target:", target["centroid_bottom_in"])
    print("  I11_in4:", exp_i11, "delta_from_baseline:", exp_i11 - base_i11, "target:", target["I11_in4"])
    print("  I22_in4:", exp_i22, "delta_from_baseline:", exp_i22 - base_i22, "target:", target["I22_in4"])
