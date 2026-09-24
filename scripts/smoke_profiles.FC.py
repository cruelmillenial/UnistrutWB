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
    gap_mm = float(spec["lip_tip_gap"]["mm"])

    # For a uniform-thickness formed strip, A/t is the area-equivalent
    # developed centerline length. This is independent of the current OCC
    # boundary construction and gives us a powerful inverse constraint.
    published_area_mm2 = target["area_in2"] * MM2_PER_IN2
    developed_from_area_mm = published_area_mm2 / t_mm

    shape = profiles.build_channel(profile, 1.0, mode="simple")
    actual_area_mm2 = shape.Volume
    developed_from_model_mm = actual_area_mm2 / t_mm

    side_projection_mm = (width_mm - opening_mm) / 2.0
    tip_projection_mm = (opening_mm - gap_mm) / 2.0
    naive_semicircle_radius_mm = tip_projection_mm / 2.0

    print(profile_id)
    print("  width_mm:", width_mm, "depth_mm:", depth_mm, "thickness_mm:", t_mm)
    print("  opening_mm:", opening_mm, "gap_mm:", gap_mm)
    print("  side_projection_mm:", side_projection_mm)
    print("  tip_projection_mm:", tip_projection_mm)
    print("  old_naive_semicircle_radius_mm:", naive_semicircle_radius_mm)
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
    #   moving steel downward while preserving width/opening/gap.
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
    gap = float(spec["lip_tip_gap"]["mm"])

    if lip_radius_mm <= t / 2.0:
        return None

    r_mid = float(lip_radius_mm)
    r_in = r_mid - t / 2.0
    r_out = r_mid + t / 2.0

    side_projection = (w - opening) / 2.0
    tip_projection = (opening - gap) / 2.0

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
    gap = float(spec["lip_tip_gap"]["mm"])
    max_r = (opening - gap) / 4.0

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
    gap = float(spec["lip_tip_gap"]["mm"])

    if lip_radius_mm <= t / 2.0:
        return None
    if not (55.0 <= curl_sweep_deg <= 120.0):
        return None

    r_mid = float(lip_radius_mm)
    r_in = r_mid - t / 2.0
    r_out = r_mid + t / 2.0

    side_projection = (w - opening) / 2.0
    tip_projection = (opening - gap) / 2.0

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
    line(w,0,w,z_top)
    line(w,z_top,c_right_y,z_top)

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
    line(c_left_y,z_top,0,z_top)
    line(0,z_top,0,0)

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
    gap = float(spec["lip_tip_gap"]["mm"])
    max_r = (opening-gap)/4.0

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
