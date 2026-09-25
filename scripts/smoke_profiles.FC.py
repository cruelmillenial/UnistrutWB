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
    tip_projection_mm = (opening_mm - lip_depth_mm) / 2.0
    naive_semicircle_radius_mm = tip_projection_mm / 2.0

    print(profile_id)
    print("  width_mm:", width_mm, "depth_mm:", depth_mm, "thickness_mm:", t_mm)
    print("  opening_mm:", opening_mm, "lip_depth_mm:", lip_depth_mm)
    print("  side_projection_mm:", side_projection_mm)
    print("  tip_projection_mm:", tip_projection_mm)
    print("  old_naive_lip_depth_radius_mm:", naive_semicircle_radius_mm)
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


print("\nGRID FIT: TWO-RADIUS FAMILY")

def score_candidate(*, area_in2, centroid_bottom_in, i11_in4, i22_in4, target):
    errs = {
        "area": (area_in2 - target["area_in2"]) / target["area_in2"],
        "centroid": (centroid_bottom_in - target["centroid_bottom_in"]) / target["centroid_bottom_in"],
        "i11": (i11_in4 - target["I11_in4"]) / target["I11_in4"],
        "i22": (i22_in4 - target["I22_in4"]) / target["I22_in4"],
    }
    # Equal weighting for now. Keep this intentionally simple and inspectable.
    score = sum(v * v for v in errs.values())
    return score, errs

def build_parametric_candidate(profile, *, lip_radius_mm, wall_relief_mm):
    # Diagnostic inverse-fit family:
    # - lip_radius_mm replaces the old radius implied purely from O/G
    # - wall_relief_mm shortens the effective vertical web before the curl,
    #   moving steel downward while preserving width/opening/lip_depth.
    #
    # This is not yet the production geometry model. It is deliberately a
    # minimal two-parameter family used to determine whether those degrees of
    # freedom can reconcile A, centroid, I11 and I22 simultaneously.
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])

    if lip_radius_mm <= t / 2.0:
        return None

    r_mid = float(lip_radius_mm)
    r_in = r_mid - t / 2.0
    r_out = r_mid + t / 2.0

    side_projection = (w - opening) / 2.0
    tip_projection = lip_depth

    # Preserve the published lateral tip constraint. If the selected radius
    # cannot reach the tip without a negative tangent leg, reject it.
    tangent_leg = tip_projection - 2.0 * r_mid
    if tangent_leg < -1e-6:
        return None
    tangent_leg = max(tangent_leg, 0.0)

    z_top = h - float(wall_relief_mm)
    if z_top <= t or z_top >= h + 1e-9:
        return None

    c_left_y = side_projection + r_mid
    c_right_y = w - side_projection - r_mid
    c_z = z_top - r_mid

    edges = []
    def line(y1, z1, y2, z2):
        if abs(y2-y1) < 1e-9 and abs(z2-z1) < 1e-9:
            return
        edges.append(Part.makeLine(App.Vector(0,y1,z1), App.Vector(0,y2,z2)))
    def arc3(y1,z1,ym,zm,y2,z2):
        edges.append(Part.Arc(App.Vector(0,y1,z1),App.Vector(0,ym,zm),App.Vector(0,y2,z2)).toShape())

    y_lo, y_hi, z_lo = 0.0, w, 0.0

    line(y_lo,z_lo,y_hi,z_lo)
    line(y_hi,z_lo,y_hi,z_top)
    line(y_hi,z_top,c_right_y,z_top)

    arc3(c_right_y,z_top,
         c_right_y-r_out/1.41421356237,c_z+r_out/1.41421356237,
         c_right_y-r_out,c_z)

    # Optional tangent leg toward the published lip-tip location.
    right_outer_tip = c_right_y - r_out
    right_outer_end = right_outer_tip - tangent_leg
    line(right_outer_tip,c_z,right_outer_end,c_z)
    line(right_outer_end,c_z,right_outer_end+t,c_z)

    right_inner_start = c_right_y - r_in
    if abs((right_outer_end+t) - right_inner_start) > 1e-6:
        line(right_outer_end+t,c_z,right_inner_start,c_z)

    arc3(c_right_y-r_in,c_z,
         c_right_y-r_in/1.41421356237,c_z+r_in/1.41421356237,
         c_right_y,c_z+r_in)

    line(c_right_y,c_z+r_in,w-t,z_top-t)
    line(w-t,z_top-t,w-t,t)
    line(w-t,t,t,t)
    line(t,t,t,z_top-t)
    line(t,z_top-t,c_left_y,c_z+r_in)

    arc3(c_left_y,c_z+r_in,
         c_left_y+r_in/1.41421356237,c_z+r_in/1.41421356237,
         c_left_y+r_in,c_z)

    left_inner_tip = c_left_y + r_in
    left_inner_end = left_inner_tip + tangent_leg
    line(left_inner_tip,c_z,left_inner_end,c_z)
    line(left_inner_end,c_z,left_inner_end+t,c_z)

    left_outer_start = c_left_y + r_out
    if abs((left_inner_end+t) - left_outer_start) > 1e-6:
        line(left_inner_end+t,c_z,left_outer_start,c_z)

    arc3(c_left_y+r_out,c_z,
         c_left_y+r_out/1.41421356237,c_z+r_out/1.41421356237,
         c_left_y,z_top)

    line(c_left_y,z_top,y_lo,z_top)
    line(y_lo,z_top,y_lo,z_lo)

    wire = Part.Wire(edges)
    if not wire.isClosed():
        return None
    face = Part.Face(wire)
    if face.isNull() or not face.isValid():
        return None
    solid = face.extrude(App.Vector(1.0,0,0))
    if solid.isNull() or not solid.isValid():
        return None
    return solid

grid_targets = fit_targets

for profile_id, target in grid_targets.items():
    profile = cat.get_profile(profile_id)
    best = None

    # Broad coarse grid; small enough to run interactively in FreeCAD.
    # Radius starts just above t/2 and stops at O/G-derived projection/2.
    spec = profile["geometry"]["profile_spec"]
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])
    max_r = lip_depth / 2.0

    radius_steps = 16
    relief_steps = 16
    r0 = t/2.0 + 0.15
    r1 = max_r
    relief0 = 0.0
    relief1 = min(6.0, float(profile["geometry"]["height"]["mm"]) * 0.25)

    for i in range(radius_steps + 1):
        r = r0 + (r1-r0) * i / radius_steps
        for j in range(relief_steps + 1):
            relief = relief0 + (relief1-relief0) * j / relief_steps
            shape = build_parametric_candidate(profile, lip_radius_mm=r, wall_relief_mm=relief)
            if shape is None:
                continue

            area_in2 = shape.Volume / MM2_PER_IN2
            centroid_bottom_in = shape.CenterOfMass.z / MM_PER_IN
            moi = shape.MatrixOfInertia
            i11_in4 = moi.A22 / IN4_TO_MM4
            i22_in4 = moi.A33 / IN4_TO_MM4

            score, errs = score_candidate(
                area_in2=area_in2,
                centroid_bottom_in=centroid_bottom_in,
                i11_in4=i11_in4,
                i22_in4=i22_in4,
                target=target,
            )
            row = (score, r, relief, area_in2, centroid_bottom_in, i11_in4, i22_in4, errs)
            if best is None or score < best[0]:
                best = row

    print(profile_id)
    if best is None:
        print("  no valid candidates")
        continue

    score, r, relief, area_in2, centroid_bottom_in, i11_in4, i22_in4, errs = best
    print("  best_score:", score)
    print("  lip_radius_mm:", r)
    print("  wall_relief_mm:", relief)
    print("  area_in2:", area_in2, "target:", target["area_in2"])
    print("  centroid_bottom_in:", centroid_bottom_in, "target:", target["centroid_bottom_in"])
    print("  I11_in4:", i11_in4, "target:", target["I11_in4"])
    print("  I22_in4:", i22_in4, "target:", target["I22_in4"])
    print("  rel_errors:", errs)


print("\nGRID FIT: THREE-PARAMETER CURL FAMILY")

def build_parametric_candidate_v2(profile, *, lip_radius_mm, wall_relief_mm, curl_sweep_deg):
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])

    if lip_radius_mm <= t / 2.0:
        return None
    if not (55.0 <= curl_sweep_deg <= 120.0):
        return None

    r_mid = float(lip_radius_mm)
    r_in = r_mid - t / 2.0
    r_out = r_mid + t / 2.0

    side_projection = (w - opening) / 2.0
    tip_projection = lip_depth

    theta = math.radians(float(curl_sweep_deg))
    lateral_from_arc = r_mid * math.sin(theta)
    tangent_leg = tip_projection - lateral_from_arc
    if tangent_leg < -1e-6:
        return None
    tangent_leg = max(tangent_leg, 0.0)

    z_top = h - float(wall_relief_mm)
    if z_top <= t or z_top >= h + 1e-9:
        return None

    edges = []
    def line(y1,z1,y2,z2):
        if abs(y2-y1) < 1e-9 and abs(z2-z1) < 1e-9:
            return
        edges.append(Part.makeLine(App.Vector(0,y1,z1), App.Vector(0,y2,z2)))
    def arc_pts(cy,cz,r,a0,a1):
        am = 0.5*(a0+a1)
        p0 = App.Vector(0, cy + r*math.cos(a0), cz + r*math.sin(a0))
        pm = App.Vector(0, cy + r*math.cos(am), cz + r*math.sin(am))
        p1 = App.Vector(0, cy + r*math.cos(a1), cz + r*math.sin(a1))
        edges.append(Part.Arc(p0,pm,p1).toShape())

    # Right curl: start at top, rotate inward/down by sweep.
    c_right_y = w - side_projection - r_mid
    c_z = z_top - r_mid

    line(0,0,w,0)
    # z_top is the centerline crown.  The material's outer boundary is
    # t/2 above it at the crown, while the inner boundary is t/2 below it.
    # Keep the outer web/top boundary on the actual r_out tangent point so
    # the boundary wire is topologically closed.
    z_outer_crown = c_z + r_out
    line(w,0,w,z_outer_crown)
    line(w,z_outer_crown,c_right_y,z_outer_crown)

    a0 = math.pi/2.0
    a1 = math.pi/2.0 + theta
    arc_pts(c_right_y,c_z,r_out,a0,a1)
    ro_y = c_right_y + r_out*math.cos(a1)
    ro_z = c_z + r_out*math.sin(a1)

    tan_y = -math.sin(a1)
    tan_z = math.cos(a1)
    line(ro_y,ro_z,ro_y+tangent_leg*tan_y,ro_z+tangent_leg*tan_z)

    ri_end_y = c_right_y + r_in*math.cos(a1)
    ri_end_z = c_z + r_in*math.sin(a1)
    outer_tip_y = ro_y+tangent_leg*tan_y
    outer_tip_z = ro_z+tangent_leg*tan_z
    line(outer_tip_y,outer_tip_z,ri_end_y+tangent_leg*tan_y,ri_end_z+tangent_leg*tan_z)
    line(ri_end_y+tangent_leg*tan_y,ri_end_z+tangent_leg*tan_z,ri_end_y,ri_end_z)

    arc_pts(c_right_y,c_z,r_in,a1,a0)
    line(c_right_y,c_z+r_in,w-t,z_top-t)
    line(w-t,z_top-t,w-t,t)
    line(w-t,t,t,t)
    line(t,t,t,z_top-t)

    # Left side mirrors the right.
    c_left_y = side_projection + r_mid
    line(t,z_top-t,c_left_y,c_z+r_in)

    la0 = math.pi/2.0
    la1 = math.pi/2.0 - theta
    arc_pts(c_left_y,c_z,r_in,la0,la1)
    li_end_y = c_left_y + r_in*math.cos(la1)
    li_end_z = c_z + r_in*math.sin(la1)

    ltan_y = -math.sin(la1)
    ltan_z = math.cos(la1)
    line(li_end_y,li_end_z,li_end_y+tangent_leg*ltan_y,li_end_z+tangent_leg*ltan_z)

    lo_end_y = c_left_y + r_out*math.cos(la1)
    lo_end_z = c_z + r_out*math.sin(la1)
    line(li_end_y+tangent_leg*ltan_y,li_end_z+tangent_leg*ltan_z,
         lo_end_y+tangent_leg*ltan_y,lo_end_z+tangent_leg*ltan_z)
    line(lo_end_y+tangent_leg*ltan_y,lo_end_z+tangent_leg*ltan_z,lo_end_y,lo_end_z)

    arc_pts(c_left_y,c_z,r_out,la1,la0)
    line(c_left_y,z_outer_crown,0,z_outer_crown)
    line(0,z_outer_crown,0,0)

    try:
        wire = Part.Wire(edges)
        if not wire.isClosed():
            return None
        face = Part.Face(wire)
        if face.isNull() or not face.isValid():
            return None
        solid = face.extrude(App.Vector(1.0,0,0))
        if solid.isNull() or not solid.isValid():
            return None
        return solid
    except Exception:
        return None

for profile_id, target in fit_targets.items():
    profile = cat.get_profile(profile_id)
    spec = profile["geometry"]["profile_spec"]
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])
    max_r = lip_depth/2.0

    best = None
    valid_count = 0

    # Coarse exploratory grid. Keep runtime tolerable in the FreeCAD console.
    for ri in range(9):
        r = (t/2.0 + 0.15) + (max_r-(t/2.0+0.15))*ri/8.0
        for rli in range(9):
            relief = min(6.0,float(profile["geometry"]["height"]["mm"])*0.25)*rli/8.0
            for si in range(9):
                sweep = 60.0 + 60.0*si/8.0
                shape = build_parametric_candidate_v2(profile, lip_radius_mm=r, wall_relief_mm=relief, curl_sweep_deg=sweep)
                if shape is None:
                    continue
                valid_count += 1

                area_in2 = shape.Volume/MM2_PER_IN2
                centroid_bottom_in = shape.CenterOfMass.z/MM_PER_IN
                moi = shape.MatrixOfInertia
                i11_in4 = moi.A22/IN4_TO_MM4
                i22_in4 = moi.A33/IN4_TO_MM4

                score, errs = score_candidate(
                    area_in2=area_in2,
                    centroid_bottom_in=centroid_bottom_in,
                    i11_in4=i11_in4,
                    i22_in4=i22_in4,
                    target=target,
                )
                row=(score,r,relief,sweep,area_in2,centroid_bottom_in,i11_in4,i22_in4,errs)
                if best is None or score < best[0]:
                    best=row

    print(profile_id)
    print("  valid_candidates:", valid_count)
    if best is None:
        print("  no valid candidates")
        continue

    score,r,relief,sweep,area_in2,centroid_bottom_in,i11_in4,i22_in4,errs=best
    print("  best_score:",score)
    print("  lip_radius_mm:",r)
    print("  wall_relief_mm:",relief)
    print("  curl_sweep_deg:",sweep)
    print("  area_in2:",area_in2,"target:",target["area_in2"])
    print("  centroid_bottom_in:",centroid_bottom_in,"target:",target["centroid_bottom_in"])
    print("  I11_in4:",i11_in4,"target:",target["I11_in4"])
    print("  I22_in4:",i22_in4,"target:",target["I22_in4"])
    print("  rel_errors:",errs)


print("\nTHREE-PARAMETER SINGLE-CANDIDATE TRACE")

def trace_parametric_candidate(profile_id, *, lip_radius_mm, wall_relief_mm, curl_sweep_deg):
    profile = cat.get_profile(profile_id)
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])

    print(profile_id)
    print("  params:", {"lip_radius_mm": lip_radius_mm, "wall_relief_mm": wall_relief_mm, "curl_sweep_deg": curl_sweep_deg})

    try:
        r_mid = float(lip_radius_mm)
        r_in = r_mid - t/2.0
        r_out = r_mid + t/2.0
        side_projection = (w-opening)/2.0
        tip_projection = (opening-lip_depth)/2.0
        theta = math.radians(float(curl_sweep_deg))
        lateral_from_arc = r_mid * math.sin(theta)
        tangent_leg = tip_projection - lateral_from_arc
        z_top = h - float(wall_relief_mm)

        print("  derived:", {
            "r_in": r_in,
            "r_out": r_out,
            "side_projection": side_projection,
            "tip_projection": tip_projection,
            "lateral_from_arc": lateral_from_arc,
            "tangent_leg": tangent_leg,
            "z_top": z_top,
        })

        if r_in <= 0:
            print("  FAIL: non-positive inner radius")
            return
        if tangent_leg < -1e-6:
            print("  FAIL: negative tangent leg")
            return
        if z_top <= t or z_top >= h + 1e-9:
            print("  FAIL: invalid z_top")
            return

        shape = build_parametric_candidate_v2(
            profile,
            lip_radius_mm=lip_radius_mm,
            wall_relief_mm=wall_relief_mm,
            curl_sweep_deg=curl_sweep_deg,
        )
        if shape is None:
            print("  FAIL: builder returned None; likely wire/face/solid validity")
            return

        print("  PASS")
        print("  BB:", shape.BoundBox.XLength, shape.BoundBox.YLength, shape.BoundBox.ZLength)
        print("  area_in2:", shape.Volume/MM2_PER_IN2)
        print("  centroid_bottom_in:", shape.CenterOfMass.z/MM_PER_IN)
        moi = shape.MatrixOfInertia
        print("  I11_in4:", moi.A22/IN4_TO_MM4)
        print("  I22_in4:", moi.A33/IN4_TO_MM4)
    except Exception as exc:
        print("  EXCEPTION:", type(exc).__name__, str(exc))

trace_parametric_candidate(
    "P1000",
    lip_radius_mm=3.7703125,
    wall_relief_mm=3.375,
    curl_sweep_deg=90.0,
)
trace_parametric_candidate(
    "P4100",
    lip_radius_mm=3.96875,
    wall_relief_mm=1.934765625,
    curl_sweep_deg=90.0,
)


print("\nTHREE-PARAMETER EDGE TRACE")

def trace_candidate_edges(profile_id, *, lip_radius_mm, wall_relief_mm, curl_sweep_deg):
    profile = cat.get_profile(profile_id)
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])

    r_mid = float(lip_radius_mm)
    r_in = r_mid - t/2.0
    r_out = r_mid + t/2.0
    side_projection = (w-opening)/2.0
    tip_projection = (opening-lip_depth)/2.0
    theta = math.radians(float(curl_sweep_deg))
    tangent_leg = max(0.0, tip_projection - r_mid*math.sin(theta))
    z_top = h - float(wall_relief_mm)
    c_z = z_top-r_mid
    c_right_y = w-side_projection-r_mid
    c_left_y = side_projection+r_mid

    pts=[]
    def add(label,y,z):
        pts.append((label,float(y),float(z)))

    add("bottom-left",0,0)
    add("bottom-right",w,0)
    add("right-top-outer",w,z_top)
    add("right-arc-start",c_right_y,z_top)

    a0=math.pi/2.0
    a1=math.pi/2.0+theta
    ro_y=c_right_y+r_out*math.cos(a1); ro_z=c_z+r_out*math.sin(a1)
    add("right-arc-outer-end",ro_y,ro_z)
    tan_y=-math.sin(a1); tan_z=math.cos(a1)
    rot_y=ro_y+tangent_leg*tan_y; rot_z=ro_z+tangent_leg*tan_z
    add("right-outer-tip",rot_y,rot_z)

    ri_y=c_right_y+r_in*math.cos(a1); ri_z=c_z+r_in*math.sin(a1)
    rit_y=ri_y+tangent_leg*tan_y; rit_z=ri_z+tangent_leg*tan_z
    add("right-inner-tip-offset",rit_y,rit_z)
    add("right-arc-inner-end",ri_y,ri_z)
    add("right-arc-inner-start",c_right_y,c_z+r_in)
    add("right-web-inner-top",w-t,z_top-t)
    add("right-web-inner-bottom",w-t,t)
    add("left-web-inner-bottom",t,t)
    add("left-web-inner-top",t,z_top-t)
    add("left-arc-inner-start",c_left_y,c_z+r_in)

    la1=math.pi/2.0-theta
    li_y=c_left_y+r_in*math.cos(la1); li_z=c_z+r_in*math.sin(la1)
    lty=-math.sin(la1); ltz=math.cos(la1)
    lit_y=li_y+tangent_leg*lty; lit_z=li_z+tangent_leg*ltz
    add("left-arc-inner-end",li_y,li_z)
    add("left-inner-tip-offset",lit_y,lit_z)

    lo_y=c_left_y+r_out*math.cos(la1); lo_z=c_z+r_out*math.sin(la1)
    lot_y=lo_y+tangent_leg*lty; lot_z=lo_z+tangent_leg*ltz
    add("left-outer-tip",lot_y,lot_z)
    add("left-arc-outer-end",lo_y,lo_z)
    add("left-arc-outer-start",c_left_y,z_top)
    add("left-top-outer",0,z_top)

    print(profile_id)
    for label,y,z in pts:
        print(" ",label,":",y,z)

    # Cheap diagnostics before OCC: detect exact duplicate consecutive points
    # and gross envelope violations.
    dupes=[]
    for (la,ya,za),(lb,yb,zb) in zip(pts,pts[1:]):
        if abs(ya-yb)<1e-9 and abs(za-zb)<1e-9:
            dupes.append((la,lb))
    print("  duplicate_consecutive_points:",dupes)
    ys=[p[1] for p in pts]; zs=[p[2] for p in pts]
    print("  point_envelope_y:",min(ys),max(ys),"nominal:",0,w)
    print("  point_envelope_z:",min(zs),max(zs),"nominal:",0,h)

trace_candidate_edges("P1000",lip_radius_mm=3.7703125,wall_relief_mm=3.375,curl_sweep_deg=90.0)
trace_candidate_edges("P4100",lip_radius_mm=3.96875,wall_relief_mm=1.934765625,curl_sweep_deg=90.0)


print("\nTHREE-PARAMETER BUILDER FAILURE STAGE TRACE")

def trace_builder_stage(profile_id, *, lip_radius_mm, wall_relief_mm, curl_sweep_deg):
    profile = cat.get_profile(profile_id)
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])

    r_mid = float(lip_radius_mm)
    r_in = r_mid - t/2.0
    r_out = r_mid + t/2.0
    side_projection = (w-opening)/2.0
    tip_projection = (opening-lip_depth)/2.0
    theta = math.radians(float(curl_sweep_deg))
    tangent_leg = max(0.0, tip_projection - r_mid*math.sin(theta))
    z_top = h - float(wall_relief_mm)
    c_z = z_top-r_mid
    c_right_y = w-side_projection-r_mid
    c_left_y = side_projection+r_mid

    edges=[]
    labels=[]
    def line(label,y1,z1,y2,z2):
        if abs(y2-y1)<1e-9 and abs(z2-z1)<1e-9:
            return
        edges.append(Part.makeLine(App.Vector(0,y1,z1),App.Vector(0,y2,z2)))
        labels.append(label)
    def arc(label,cy,cz,r,a0,a1):
        am=0.5*(a0+a1)
        p0=App.Vector(0,cy+r*math.cos(a0),cz+r*math.sin(a0))
        pm=App.Vector(0,cy+r*math.cos(am),cz+r*math.sin(am))
        p1=App.Vector(0,cy+r*math.cos(a1),cz+r*math.sin(a1))
        edges.append(Part.Arc(p0,pm,p1).toShape())
        labels.append(label)

    try:
        line("bottom",0,0,w,0)
        line("right_outer_web",w,0,w,z_top)
        line("right_top_outer",w,z_top,c_right_y,z_top)
        a0=math.pi/2; a1=math.pi/2+theta
        arc("right_outer_arc",c_right_y,c_z,r_out,a0,a1)
        ro_y=c_right_y+r_out*math.cos(a1); ro_z=c_z+r_out*math.sin(a1)
        ty=-math.sin(a1); tz=math.cos(a1)
        line("right_outer_tangent",ro_y,ro_z,ro_y+tangent_leg*ty,ro_z+tangent_leg*tz)
        ri_y=c_right_y+r_in*math.cos(a1); ri_z=c_z+r_in*math.sin(a1)
        rot_y=ro_y+tangent_leg*ty; rot_z=ro_z+tangent_leg*tz
        rit_y=ri_y+tangent_leg*ty; rit_z=ri_z+tangent_leg*tz
        line("right_tip_thickness",rot_y,rot_z,rit_y,rit_z)
        line("right_inner_tangent",rit_y,rit_z,ri_y,ri_z)
        arc("right_inner_arc",c_right_y,c_z,r_in,a1,a0)
        line("right_arc_to_inner_web",c_right_y,c_z+r_in,w-t,z_top-t)
        line("right_inner_web",w-t,z_top-t,w-t,t)
        line("inner_bottom",w-t,t,t,t)
        line("left_inner_web",t,t,t,z_top-t)
        line("left_inner_web_to_arc",t,z_top-t,c_left_y,c_z+r_in)
        la0=math.pi/2; la1=math.pi/2-theta
        arc("left_inner_arc",c_left_y,c_z,r_in,la0,la1)
        li_y=c_left_y+r_in*math.cos(la1); li_z=c_z+r_in*math.sin(la1)
        lty=-math.sin(la1); ltz=math.cos(la1)
        lit_y=li_y+tangent_leg*lty; lit_z=li_z+tangent_leg*ltz
        line("left_inner_tangent",li_y,li_z,lit_y,lit_z)
        lo_y=c_left_y+r_out*math.cos(la1); lo_z=c_z+r_out*math.sin(la1)
        lot_y=lo_y+tangent_leg*lty; lot_z=lo_z+tangent_leg*ltz
        line("left_tip_thickness",lit_y,lit_z,lot_y,lot_z)
        line("left_outer_tangent",lot_y,lot_z,lo_y,lo_z)
        arc("left_outer_arc",c_left_y,c_z,r_out,la1,la0)
        line("left_top_outer",c_left_y,z_top,0,z_top)
        line("left_outer_web",0,z_top,0,0)

        print(profile_id)
        print("  edges_built:",len(edges))
        for i,e in enumerate(edges):
            print("   ",i,labels[i],"len:",e.Length)

        wire=Part.Wire(edges)
        print("  wire_is_closed:",wire.isClosed())
        print("  wire_is_valid:",wire.isValid())
        print("  wire_length:",wire.Length)
        if not wire.isClosed() or not wire.isValid():
            print("  FAIL_STAGE: wire")
            return

        face=Part.Face(wire)
        print("  face_is_null:",face.isNull())
        print("  face_is_valid:",face.isValid())
        print("  face_area:",face.Area)
        if face.isNull() or not face.isValid():
            print("  FAIL_STAGE: face")
            return

        solid=face.extrude(App.Vector(1.0,0,0))
        print("  solid_is_null:",solid.isNull())
        print("  solid_is_valid:",solid.isValid())
        print("  solid_volume:",solid.Volume)
        if solid.isNull() or not solid.isValid():
            print("  FAIL_STAGE: solid")
            return

        print("  PASS")
    except Exception as exc:
        print(profile_id)
        print("  EXCEPTION_STAGE:", type(exc).__name__, str(exc))

trace_builder_stage("P1000",lip_radius_mm=3.7703125,wall_relief_mm=3.375,curl_sweep_deg=90.0)
trace_builder_stage("P4100",lip_radius_mm=3.96875,wall_relief_mm=1.934765625,curl_sweep_deg=90.0)


print("\nTHREE-PARAMETER EDGE-JOIN GAPS")

def trace_edge_join_lip_depths(profile_id, *, lip_radius_mm, wall_relief_mm, curl_sweep_deg):
    profile = cat.get_profile(profile_id)
    geom = profile["geometry"]
    spec = geom["profile_spec"]
    w = float(geom["width"]["mm"])
    h = float(geom["height"]["mm"])
    t = float(spec["t"]["mm"])
    opening = float(spec["mouth_opening"]["mm"])
    lip_depth = float(spec["lip_depth"]["mm"])
    r_mid = float(lip_radius_mm)
    r_in = r_mid - t/2.0
    r_out = r_mid + t/2.0
    side_projection = (w-opening)/2.0
    tip_projection = (opening-lip_depth)/2.0
    theta = math.radians(float(curl_sweep_deg))
    tangent_leg = max(0.0, tip_projection-r_mid*math.sin(theta))
    z_top = h-float(wall_relief_mm)
    c_z = z_top-r_mid
    c_right_y = w-side_projection-r_mid
    c_left_y = side_projection+r_mid

    edges=[]; labels=[]
    def line(label,y1,z1,y2,z2):
        edges.append(Part.makeLine(App.Vector(0,y1,z1),App.Vector(0,y2,z2))); labels.append(label)
    def arc(label,cy,cz,r,a0,a1):
        am=.5*(a0+a1)
        edges.append(Part.Arc(
            App.Vector(0,cy+r*math.cos(a0),cz+r*math.sin(a0)),
            App.Vector(0,cy+r*math.cos(am),cz+r*math.sin(am)),
            App.Vector(0,cy+r*math.cos(a1),cz+r*math.sin(a1))).toShape()); labels.append(label)

    a0=math.pi/2; a1=math.pi/2+theta
    line("bottom",0,0,w,0)
    line("right_outer_web",w,0,w,z_top)
    line("right_top_outer",w,z_top,c_right_y,z_top)
    arc("right_outer_arc",c_right_y,c_z,r_out,a0,a1)
    ro_y=c_right_y+r_out*math.cos(a1); ro_z=c_z+r_out*math.sin(a1)
    ty=-math.sin(a1); tz=math.cos(a1)
    rot_y=ro_y+tangent_leg*ty; rot_z=ro_z+tangent_leg*tz
    line("right_outer_tangent",ro_y,ro_z,rot_y,rot_z)
    ri_y=c_right_y+r_in*math.cos(a1); ri_z=c_z+r_in*math.sin(a1)
    rit_y=ri_y+tangent_leg*ty; rit_z=ri_z+tangent_leg*tz
    line("right_tip_thickness",rot_y,rot_z,rit_y,rit_z)
    line("right_inner_tangent",rit_y,rit_z,ri_y,ri_z)
    arc("right_inner_arc",c_right_y,c_z,r_in,a1,a0)
    line("right_arc_to_inner_web",c_right_y,c_z+r_in,w-t,z_top-t)
    line("right_inner_web",w-t,z_top-t,w-t,t)
    line("inner_bottom",w-t,t,t,t)
    line("left_inner_web",t,t,t,z_top-t)
    line("left_inner_web_to_arc",t,z_top-t,c_left_y,c_z+r_in)
    la0=math.pi/2; la1=math.pi/2-theta
    arc("left_inner_arc",c_left_y,c_z,r_in,la0,la1)
    li_y=c_left_y+r_in*math.cos(la1); li_z=c_z+r_in*math.sin(la1)
    lty=-math.sin(la1); ltz=math.cos(la1)
    lit_y=li_y+tangent_leg*lty; lit_z=li_z+tangent_leg*ltz
    line("left_inner_tangent",li_y,li_z,lit_y,lit_z)
    lo_y=c_left_y+r_out*math.cos(la1); lo_z=c_z+r_out*math.sin(la1)
    lot_y=lo_y+tangent_leg*lty; lot_z=lo_z+tangent_leg*ltz
    line("left_tip_thickness",lit_y,lit_z,lot_y,lot_z)
    line("left_outer_tangent",lot_y,lot_z,lo_y,lo_z)
    arc("left_outer_arc",c_left_y,c_z,r_out,la1,la0)
    line("left_top_outer",c_left_y,z_top,0,z_top)
    line("left_outer_web",0,z_top,0,0)

    print(profile_id)
    max_lip_depth=0.0
    for i,e in enumerate(edges):
        n=(i+1)%len(edges)
        lip_depth=(e.Vertexes[-1].Point-edges[n].Vertexes[0].Point).Length
        max_lip_depth=max(max_lip_depth,lip_depth)
        if lip_depth > 1e-7:
            print(" ",labels[i],"->",labels[n],"lip_depth_mm:",lip_depth,
                  "from:",tuple(e.Vertexes[-1].Point),
                  "to:",tuple(edges[n].Vertexes[0].Point))
    print("  max_join_lip_depth_mm:",max_lip_depth)

trace_edge_join_lip_depths("P1000",lip_radius_mm=3.7703125,wall_relief_mm=3.375,curl_sweep_deg=90.0)
trace_edge_join_lip_depths("P4100",lip_radius_mm=3.96875,wall_relief_mm=1.934765625,curl_sweep_deg=90.0)
