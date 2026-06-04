# Assembly Reference Schema

## Purpose

This document defines the proposed schema contract for Assembly-facing references in UnistrutWB catalog records.

UnistrutWB does not solve final assemblies. It should generate catalog-aware CAD objects with enough metadata and reference intent for FreeCAD Assembly or downstream tools to constrain them cleanly.

## Scope

This schema applies to catalog records for:

- channel profiles
- fittings
- future hardware presets where useful

The first Phase 1 targets are:

- `P4100`
- `P1065`
- `DEV_ANGLE_90_2LEG`

## Top-level schema fields

Catalog records may define Assembly-facing references using these fields:

    reference_geometry
    mate_frames
    reference_groups

These fields are descriptive first. They do not require immediate creation of real FreeCAD Datum/LCS geometry, but they define the intended names and roles.

## reference_geometry

`reference_geometry` describes named planes, axes, points, or lines that should eventually be exposed as selectable geometry or preserved as metadata.

### Shape

    "reference_geometry": [
      {
        "id": "Plane_OpenFace",
        "kind": "plane",
        "role": "open_face",
        "description": "Plane representing the channel open face",
        "local_origin": "profile_origin",
        "normal": "local_z_negative"
      }
    ]

### Required keys

    id
    kind
    role

### Optional keys

    description
    local_origin
    normal
    axis
    point
    derived_from
    applies_to
    count
    pattern

### Allowed kind values

    plane
    axis
    line
    point
    point_array
    face
    edge
    datum
    lcs

### Common role values

    open_face
    back_face
    mounting_face
    longitudinal_axis
    slot_centerline
    slot_center
    end_plane
    hole_axis
    hole_center
    bend_line
    corner_point

## mate_frames

`mate_frames` describes named local coordinate systems intended for downstream mating and constraints.

### Current simple shape

Existing records may use:

    "mate_frames": [
      { "id": "A", "kind": "LCS" }
    ]

### Target shape

Records should evolve toward:

    "mate_frames": [
      {
        "id": "A",
        "kind": "LCS",
        "role": "mounting_face",
        "target": "Plane_MountingFace",
        "origin": "Point_Center",
        "x_axis": "local_x",
        "z_axis": "mounting_normal",
        "description": "Primary mounting frame"
      }
    ]

### Required keys

    id
    kind
    role

### Optional keys

    target
    origin
    x_axis
    y_axis
    z_axis
    description
    applies_to
    group

### Allowed kind values

    LCS
    datum
    metadata_only

### Common role values

    mounting_face
    open_face_mount
    leg_a_mounting_face
    leg_b_mounting_face
    splice_center
    hole_group
    end_mount
    debug_marker

## reference_groups

`reference_groups` collects related references into named groups.

This is useful for hole groups, slot groups, or multi-leg fittings.

### Shape

    "reference_groups": [
      {
        "id": "Group_Holes_All",
        "role": "hole_group",
        "members": ["Point_Hole_1", "Point_Hole_2"],
        "description": "All hole center references for this fitting"
      }
    ]

### Required keys

    id
    role
    members

### Optional keys

    description
    applies_to
    pattern
    count

## Coordinate convention

Current generated channel objects are treated as:

    local X = channel length
    local Y = channel width
    local Z = channel depth

For current generated P4100-style channels:

    open_face = low-Z slot/reference side

This is provisional and should eventually be defined per profile family.

## Phase 1 profile contract: P4100

### Required reference_geometry

    "reference_geometry": [
      {
        "id": "Axis_Longitudinal",
        "kind": "axis",
        "role": "longitudinal_axis",
        "axis": "local_x",
        "description": "Channel length axis"
      },
      {
        "id": "Plane_OpenFace",
        "kind": "plane",
        "role": "open_face",
        "normal": "local_z_negative",
        "description": "Open/channel-nut side of the channel"
      },
      {
        "id": "Plane_BackFace",
        "kind": "plane",
        "role": "back_face",
        "normal": "local_z_positive",
        "description": "Back/web side opposite the open face"
      },
      {
        "id": "Line_SlotCenterline",
        "kind": "line",
        "role": "slot_centerline",
        "axis": "local_x",
        "description": "Longitudinal centerline of the slot pattern"
      },
      {
        "id": "Point_EndA",
        "kind": "point",
        "role": "end_point",
        "description": "Start/end reference for the channel"
      },
      {
        "id": "Point_EndB",
        "kind": "point",
        "role": "end_point",
        "description": "Opposite end reference for the channel"
      },
      {
        "id": "SlotCenters",
        "kind": "point_array",
        "role": "slot_center",
        "description": "Generated slot center points"
      }
    ]

### Required object properties

    UnistrutType = profile
    ProfileId
    Finish
    Length
    SlotCenters

### Intended downstream use

- constrain channel end-to-end
- align fittings to open face
- align splice plates to slot centers
- use longitudinal axis for Assembly alignment

## Phase 1 fitting contract: P1065

`P1065` is currently treated as a 2-hole flat splice plate.

### Required reference_geometry

    "reference_geometry": [
      {
        "id": "Plane_MountingFace",
        "kind": "plane",
        "role": "mounting_face",
        "normal": "local_z_negative",
        "description": "Primary mounting face of the splice plate"
      },
      {
        "id": "Point_Center",
        "kind": "point",
        "role": "center",
        "description": "Plate center reference"
      },
      {
        "id": "Axis_Hole_1",
        "kind": "axis",
        "role": "hole_axis",
        "description": "Axis through hole 1"
      },
      {
        "id": "Axis_Hole_2",
        "kind": "axis",
        "role": "hole_axis",
        "description": "Axis through hole 2"
      },
      {
        "id": "Point_Hole_1",
        "kind": "point",
        "role": "hole_center",
        "description": "Hole 1 center point"
      },
      {
        "id": "Point_Hole_2",
        "kind": "point",
        "role": "hole_center",
        "description": "Hole 2 center point"
      }
    ]

### Required reference_groups

    "reference_groups": [
      {
        "id": "Group_Holes_All",
        "role": "hole_group",
        "members": ["Point_Hole_1", "Point_Hole_2"],
        "description": "All splice plate hole centers"
      }
    ]

### Required mate_frames

    "mate_frames": [
      {
        "id": "A",
        "kind": "LCS",
        "role": "mounting_face",
        "target": "Plane_MountingFace",
        "origin": "Point_Center",
        "x_axis": "local_x",
        "z_axis": "mounting_normal",
        "description": "Primary mounting frame centered on splice plate"
      }
    ]

### Required object properties

    UnistrutType = fitting
    FittingId = P1065
    FamilyId = flat_splice_plate
    FittingType = splice_plate
    Category = splice_plates
    VariantLabel = 2-Hole Splice Plate
    HoleCount = 2
    HoleDiameterIn
    HardwarePreset
    MateFrames

### Intended downstream use

- mate `Plane_MountingFace` to channel `Plane_OpenFace`
- align hole centers or axes to channel slot centerline
- allow Assembly to solve final plate position
- avoid encoding splice-joint solving inside UnistrutWB

## Phase 1 fitting contract: DEV_ANGLE_90_2LEG

`DEV_ANGLE_90_2LEG` is currently a provisional angle plate.

### Required reference_geometry

    "reference_geometry": [
      {
        "id": "Plane_LegA_MountingFace",
        "kind": "plane",
        "role": "leg_a_mounting_face",
        "description": "Mounting face for leg A"
      },
      {
        "id": "Plane_LegB_MountingFace",
        "kind": "plane",
        "role": "leg_b_mounting_face",
        "description": "Mounting face for leg B"
      },
      {
        "id": "Line_Bend",
        "kind": "line",
        "role": "bend_line",
        "description": "Inside bend/corner line between legs"
      },
      {
        "id": "Point_Corner",
        "kind": "point",
        "role": "corner_point",
        "description": "Corner reference point"
      }
    ]

### Optional future reference_geometry

    "reference_geometry": [
      {
        "id": "Axis_Hole_A1",
        "kind": "axis",
        "role": "hole_axis",
        "applies_to": "leg_a"
      },
      {
        "id": "Axis_Hole_B1",
        "kind": "axis",
        "role": "hole_axis",
        "applies_to": "leg_b"
      },
      {
        "id": "Point_Hole_A1",
        "kind": "point",
        "role": "hole_center",
        "applies_to": "leg_a"
      },
      {
        "id": "Point_Hole_B1",
        "kind": "point",
        "role": "hole_center",
        "applies_to": "leg_b"
      }
    ]

### Required reference_groups

    "reference_groups": [
      {
        "id": "Group_LegA",
        "role": "leg_reference_group",
        "members": ["Plane_LegA_MountingFace"]
      },
      {
        "id": "Group_LegB",
        "role": "leg_reference_group",
        "members": ["Plane_LegB_MountingFace"]
      }
    ]

### Required mate_frames

    "mate_frames": [
      {
        "id": "A",
        "kind": "LCS",
        "role": "leg_a_mounting_face",
        "target": "Plane_LegA_MountingFace",
        "origin": "Point_Corner",
        "description": "Mounting frame for leg A"
      },
      {
        "id": "B",
        "kind": "LCS",
        "role": "leg_b_mounting_face",
        "target": "Plane_LegB_MountingFace",
        "origin": "Point_Corner",
        "description": "Mounting frame for leg B"
      }
    ]

### Required object properties

    UnistrutType = fitting
    FittingId = DEV_ANGLE_90_2LEG
    FamilyId = angle_plate
    FittingType = angle_plate
    Category = angle_brackets
    VariantLabel = 90 Degree 2-Leg Angle Plate
    HoleDiameterIn
    HardwarePreset
    MateFrames

### Intended downstream use

- mate either leg to a channel face
- allow Assembly to solve final relationship
- avoid turning Add Fitting into a bracket assembly solver

## JSON evolution plan

Existing records may remain valid with simple `mate_frames` entries:

    "mate_frames": [
      { "id": "A", "kind": "LCS" }
    ]

Records should gradually evolve to include:

    role
    target
    origin
    axis hints
    description

## Fitting schema naming convention

Phase 1 fitting records should distinguish catalog identity from geometry builder dispatch.

Recommended fields:

    id
    name
    category
    display_group
    variant_label
    family_id
    type
    geometry_type

Current meanings:

    family_id = catalog/product family bucket
    type = legacy fitting type field, retained for backward compatibility
    geometry_type = explicit shape-builder discriminator used by build_fitting_shape()

Current Phase 1 examples:

    P1065:
      family_id = flat_splice_plate
      type = splice_plate
      geometry_type = splice_plate

    DEV_ANGLE_90_2LEG:
      family_id = angle_plate
      type = angle_plate
      geometry_type = angle_plate

Future migration may rename or replace `type` with a less ambiguous catalog-facing field, but `geometry_type` should remain the geometry dispatch key.

## Legacy fitting `type` field

The `type` field is deprecated for geometry dispatch.

Use `geometry_type` for selecting the shape builder.

Current compatibility behavior:

    geometry_type = preferred geometry dispatch field
    type = legacy fallback only

Do not add new semantics to `type`.

Future catalog-facing classification should use a clearer field name only after more catalog fitting families are normalized.

## Implementation phases

### Phase 1 — schema metadata

- document reference fields
- add richer `mate_frames` entries to `fittings.json`
- preserve mate-frame metadata on generated objects

### Phase 2 — debug/reference markers

- create simple visible markers or metadata-only stand-ins
- expose reference names for validation
- avoid full Assembly automation

### Phase 3 — Assembly-friendly references

- add real selectable reference geometry where practical
- test generated objects in FreeCAD Assembly
- refine the schema based on actual Assembly behavior

## Non-goals

This schema does not require UnistrutWB to:

- solve assemblies
- infer multi-channel joints
- place fasteners automatically
- determine bolt stack lengths
- manage Assembly constraints
- replace FreeCAD Assembly
- replace FreeCAD Fasteners

## Current status

This schema is the starting contract for Issue #5.

Next implementation step:

- update `fittings.json` `mate_frames` for `P1065`
- update `fittings.json` `mate_frames` for `DEV_ANGLE_90_2LEG`
- preserve richer mate-frame metadata on generated objects if current serialization drops fields
