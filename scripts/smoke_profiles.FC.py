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


print("\nINVERSE GEOMETRY CHECK")
inverse_targets = {
    "P1000": {
        "area_in2": 0.555,
        "weight_lb_per_ft": 1.89,
    },
    "P4100": {
        "area_in2": 0.290,
        # Weight is intentionally omitted until a reviewed catalog value is
        # wired into the bundled data/fixture.
    },
}
STEEL_DENSITY_LB_IN3 = 0.2836

for profile_id, target in inverse_targets.items():
    profile = cat.get_profile(profile_id)
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    width_mm = float(geom["width"]["mm"])
    depth_mm = float(geom["height"]["mm"])
    t_mm = float(spec["t"]["mm"])
    opening_mm = float(spec["mouth_opening"]["mm"])
    lip_depth_mm = float(spec["lip_depth"]["mm"])

    # For a uniform-thickness formed strip, A/t is the area-equivalent
    # developed centerline length. This is independent of the current OCC
    # boundary construction and gives us a powerful inverse constraint.
    published_area_mm2 = target["area_in2"] * MM2_PER_IN2
    developed_from_area_mm = published_area_mm2 / t_mm

    shape = profiles.build_channel(profile, 1.0, mode="simple")
    actual_area_mm2 = shape.Volume
    developed_from_model_mm = actual_area_mm2 / t_mm

    side_projection_mm = (width_mm - opening_mm) / 2.0

    print(profile_id)
    print("  width_mm:", width_mm, "depth_mm:", depth_mm, "thickness_mm:", t_mm)
    print("  opening_mm:", opening_mm, "lip_depth_mm:", lip_depth_mm)
    print("  side_projection_mm:", side_projection_mm)
    print("  published_area_mm2:", published_area_mm2)
    print("  developed_length_from_area_mm:", developed_from_area_mm)
    print("  model_area_mm2:", actual_area_mm2)
    print("  developed_length_from_model_mm:", developed_from_model_mm)
    print("  developed_length_excess_mm:", developed_from_model_mm - developed_from_area_mm)

    if "weight_lb_per_ft" in target:
        catalog_weight = target["weight_lb_per_ft"]
        weight_from_area = target["area_in2"] * 12.0 * STEEL_DENSITY_LB_IN3
        implied_density = catalog_weight / (target["area_in2"] * 12.0)
        print("  catalog_weight_lb_per_ft:", catalog_weight)
        print("  weight_from_area_at_0.2836_lb_in3:", weight_from_area)
        print("  weight_delta_lb_per_ft:", weight_from_area - catalog_weight)
        print("  implied_density_lb_in3:", implied_density)


print("\nFITNESS OBJECTIVE")
fit_targets = {
    "P1000": {
        "area_in2": 0.555,
        "centroid_bottom_in": 0.710,
        "I11_in4": 0.185,
        "I22_in4": 0.236,
    },
    "P4100": {
        "area_in2": 0.290,
        "centroid_bottom_in": 0.333,
        "I11_in4": 0.026,
        "I22_in4": 0.107,
    },
}

IN4_TO_MM4 = MM_PER_IN ** 4

for profile_id, target in fit_targets.items():
    profile = cat.get_profile(profile_id)
    shape = profiles.build_channel(profile, 1.0, mode="simple")

    # Unit-length extrusion means Volume == section area in mm^2.
    area_mm2 = shape.Volume
    centroid_z_mm = shape.CenterOfMass.z

    # FreeCAD solid inertia for a 1 mm extrusion is dominated in X by the
    # section's in-plane distribution. For now report the principal moments
    # directly as diagnostics; we will map them to catalog axes in the next
    # iteration once the cross-section model itself is parameterized.
    moi = shape.MatrixOfInertia
    ixx_mm4 = moi.A11
    iyy_mm4 = moi.A22
    izz_mm4 = moi.A33

    area_err = (area_mm2 / MM2_PER_IN2 - target["area_in2"]) / target["area_in2"]
    centroid_err = (centroid_z_mm / MM_PER_IN - target["centroid_bottom_in"]) / target["centroid_bottom_in"]

    print(profile_id)
    print("  area_rel_error:", area_err)
    print("  centroid_rel_error:", centroid_err)
    print("  raw_MOI_mm4:", {"xx": ixx_mm4, "yy": iyy_mm4, "zz": izz_mm4})
    print("  target_I11_mm4:", target["I11_in4"] * IN4_TO_MM4)
    print("  target_I22_mm4:", target["I22_in4"] * IN4_TO_MM4)
    print("  objective_seed:", area_err * area_err + centroid_err * centroid_err)



print("\nFIT SUMMARY (corrected lip semantics)")
for profile_id, target in fit_targets.items():
    profile = cat.get_profile(profile_id)
    shape = profiles.build_channel(profile, 1.0, mode="simple")
    area_in2 = shape.Volume / MM2_PER_IN2
    centroid_bottom_in = shape.CenterOfMass.z / MM_PER_IN
    moi = shape.MatrixOfInertia
    i11_in4 = moi.A22 / IN4_TO_MM4
    i22_in4 = moi.A33 / IN4_TO_MM4
    print(profile_id)
    print("  area_in2:", area_in2, "target:", target["area_in2"])
    print("  centroid_bottom_in:", centroid_bottom_in, "target:", target["centroid_bottom_in"])
    print("  I11_in4:", i11_in4, "target:", target["I11_in4"])
    print("  I22_in4:", i22_in4, "target:", target["I22_in4"])
    print("  mouth_opening_mm:", profile["geometry"]["profile_spec"]["mouth_opening"]["mm"])
    print("  lip_depth_mm:", profile["geometry"]["profile_spec"]["lip_depth"]["mm"])
