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

print("\nEXPERIMENTAL UPPER-SHOULDER BEND (checkpoint vs lower-radius)")
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

    try:
        lower = profiles.build_u_channel_lipped_experimental(
            width_mm=float(geom["width"]["mm"]),
            depth_mm=float(geom["height"]["mm"]),
            t_mm=t,
            length_mm=1.0,
            mouth_opening_mm=float(spec["mouth_opening"]["mm"]),
            lip_depth_mm=float(spec["lip_depth"]["mm"]),
            bend_radius_mm=t,
            lower_bend_radius_mm=t,
        )
        if not lower.isValid() or len(lower.Solids) != 1:
            raise RuntimeError("lower-bend result must be one valid solid")
        lm = lower.MatrixOfInertia
        print(profile_id, "LOWER BEND TEST")
        for name, value, old, goal in (
            ("area_in2", lower.Volume/MM2_PER_IN2, experimental.Volume/MM2_PER_IN2, target["area_in2"]),
            ("centroid_bottom_in", lower.CenterOfMass.z/MM_PER_IN, experimental.CenterOfMass.z/MM_PER_IN, target["centroid_bottom_in"]),
            ("I11_in4", lm.A22/IN4_TO_MM4, experimental.MatrixOfInertia.A22/IN4_TO_MM4, target["I11_in4"]),
            ("I22_in4", lm.A33/IN4_TO_MM4, experimental.MatrixOfInertia.A33/IN4_TO_MM4, target["I22_in4"]),
        ):
            print(" ", name, value, "delta_from_upper_only:", value-old, "target:", goal)
        print("  valid:", lower.isValid(), "solids:", len(lower.Solids),
              "width:", lower.BoundBox.YLength, "height:", lower.BoundBox.ZLength)
    except Exception as exc:
        print(profile_id, "LOWER BEND FAIL:", type(exc).__name__, str(exc))

    # Separate checkpoint: both main bends plus a rounded lip transition.
    try:
        lip = profiles.build_u_channel_lipped_experimental(
            width_mm=float(geom["width"]["mm"]),
            depth_mm=float(geom["height"]["mm"]),
            t_mm=t,
            length_mm=1.0,
            mouth_opening_mm=float(spec["mouth_opening"]["mm"]),
            lip_depth_mm=float(spec["lip_depth"]["mm"]),
            bend_radius_mm=t,
            lower_bend_radius_mm=t,
            lip_bend_radius_mm=0.5*t,
        )
        if not lip.isValid() or len(lip.Solids) != 1:
            raise RuntimeError("lip experiment must be one valid solid")
        print(profile_id, "LIP BEND TEST")
        for name, value, old, goal in (
            ("area_in2", lip.Volume/MM2_PER_IN2, lower.Volume/MM2_PER_IN2, target["area_in2"]),
            ("centroid_bottom_in", lip.CenterOfMass.z/MM_PER_IN, lower.CenterOfMass.z/MM_PER_IN, target["centroid_bottom_in"]),
            ("I11_in4", lip.MatrixOfInertia.A22/IN4_TO_MM4, lower.MatrixOfInertia.A22/IN4_TO_MM4, target["I11_in4"]),
            ("I22_in4", lip.MatrixOfInertia.A33/IN4_TO_MM4, lower.MatrixOfInertia.A33/IN4_TO_MM4, target["I22_in4"]),
        ):
            print(" ", name, value, "delta_from_lower:", value-old, "target:", goal)
        print("  valid:", lip.isValid(), "solids:", len(lip.Solids),
              "width:", lip.BoundBox.YLength, "height:", lip.BoundBox.ZLength)

        # GEOMETRY AUDIT: use solid/empty intersection probes, not only
        # bounding boxes or comparison with the published mass properties.
        # The mouth is measured at a Z below the rounded lip bend.
        w = float(geom["width"]["mm"])
        h = float(geom["height"]["mm"])
        opening = float(spec["mouth_opening"]["mm"])
        depth = float(spec["lip_depth"]["mm"])
        z_tip = h - depth
        z_probe = z_tip + min(0.25*t, 0.25*(depth-(1.5*t)))
        x_probe = 0.5
        tol = 1e-4
        def occupied(y, z):
            return lip.isInside(App.Vector(x_probe, y, z), tol, False)
        def check(name, actual, expected, tolerance=1e-4):
            ok = abs(actual-expected) <= tolerance
            print("   ", name, "PASS" if ok else "FAIL", "actual:", actual, "expected:", expected)
            return ok
        left_edge = (w-opening)/2.0
        right_edge = (w+opening)/2.0
        # Probe a horizontal line through the straight returns, scanning
        # transitions by bisection.  The slit between the lips must be empty.
        def boundary(lo, hi, inside_at_lo, iterations=40):
            for _ in range(iterations):
                mid = (lo+hi)/2.0
                if occupied(mid, z_probe) == inside_at_lo:
                    lo = mid
                else:
                    hi = mid
            return (lo+hi)/2.0
        print(profile_id, "GEOMETRY AUDIT")
        print("    lip probe z:", z_probe, "nominal bottom:", z_tip)
        mouth_empty = not occupied(w/2.0, z_probe)
        left_lip = occupied(left_edge-0.5*t, z_probe)
        right_lip = occupied(right_edge+0.5*t, z_probe)
        left_measured = boundary(left_edge-0.5*t, w/2.0, True) if left_lip and mouth_empty else float("nan")
        right_measured = boundary(w/2.0, right_edge+0.5*t, False) if right_lip and mouth_empty else float("nan")
        checks = [
            check("mouth_opening_mm", right_measured-left_measured, opening),
            check("lip_tip_left_y", left_measured, left_edge),
            check("lip_tip_right_y", right_measured, right_edge),
            check("lip_tip_bottom_z", z_tip, h-depth),
            check("envelope_width_mm", lip.BoundBox.YLength, w),
            check("envelope_height_mm", lip.BoundBox.ZLength, h),
        ]
        # Detect mid-plane discontinuities and unexpected voids by checking
        # transverse section topology and both halves' occupied points.
        mid = lip.slice(App.Vector(1,0,0), 0.5)
        print("    cross_section_edges:", len(mid.Edges),
              "single_solid:", len(lip.Solids) == 1,
              "center_mouth_empty:", mouth_empty)
        checks.extend([mouth_empty, left_lip, right_lip, len(lip.Solids) == 1])
        print("    GEOMETRY AUDIT:", "PASS" if all(checks) else "FAIL")
    except Exception as exc:
        print(profile_id, "LIP BEND FAIL:", type(exc).__name__, str(exc))

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
