# UnistrutWB Data Model

This document describes the current catalog and generated-object data model for UnistrutWB.

The goal is to keep catalog records explicit, schema-checkable, and useful to FreeCAD command code without turning the data files into hidden procedural logic.

## Data files

Current catalog and mapping files live under:

    Mod/UnistrutWB/data/

Important files:

    profiles.json
    fittings.json
    mapping_hole_series.json

Smoke tests live under:

    scripts/smoke_profiles_schema.py
    scripts/smoke_fittings_schema.py
    scripts/smoke_all_schema.py

## profiles.json

`profiles.json` contains channel profile records.

Top-level structure:

    {
      "profiles": [
        {
          "id": "P1000",
          "family": "1-5/8 x 1-5/8",
          "gauge": 12,
          "geometry": {},
          "finishes": [],
          "standard_lengths": {}
        }
      ]
    }

## Profile record

Required fields:

    id
    family
    gauge
    geometry
    finishes
    standard_lengths

### id

Catalog identifier for the profile.

Examples:

    P1000
    P1100
    P4000
    P4100

The profile id should be unique.

### family

Human-readable channel family.

Examples:

    1-5/8 x 1-5/8
    1-5/8 x 13/16

This is descriptive metadata, not geometry logic.

### gauge

Material gauge as an integer-like value.

Examples:

    12
    14
    16

Smoke tests require gauge to be positive.

### geometry

Geometry describes physical profile dimensions and profile-generation details.

Required geometry fields:

    width
    height
    thickness

Current optional/expected geometry fields:

    profile_spec
    piercing

Example:

    {
      "width": { "mm": 41.3 },
      "height": { "mm": 41.3 },
      "thickness": { "mm": 2.7 },
      "profile_spec": {
        "kind": "u_channel_lipped",
        "t": { "mm": 2.7 },
        "lip_return": { "mm": 9.5 }
      },
      "piercing": {
        "series": null,
        "template": null,
        "overrides": {}
      }
    }

### geometry.width

Overall outside width of the channel.

Current smoke tests require:

    geometry.width.mm

to exist and be numeric.

### geometry.height

Overall outside height of the channel.

Current smoke tests require:

    geometry.height.mm

to exist and be numeric.

### geometry.thickness

Nominal material thickness.

Current smoke tests require:

    geometry.thickness.mm

to exist and be numeric.

### geometry.profile_spec

Profile-generation specification.

For current lipped U-channel records:

    {
      "kind": "u_channel_lipped",
      "t": { "mm": 2.7 },
      "lip_return": { "mm": 9.5 }
    }

Required fields for `u_channel_lipped`:

    kind
    t
    lip_return

The smoke test requires:

    geometry.profile_spec.t.mm
    geometry.profile_spec.lip_return.mm

to exist and be positive numeric values.

### geometry.profile_spec.kind

Currently supported value:

    u_channel_lipped

This selects the channel builder behavior.

### geometry.profile_spec.t

Profile wall thickness used by the builder.

This should normally match `geometry.thickness`, but is stored separately because the profile builder consumes this field directly.

### geometry.profile_spec.lip_return

Lip return dimension used by the lipped U-channel builder.

### geometry.piercing

Piercing describes the catalog default piercing state for a profile.

Example plain profile:

    {
      "series": null,
      "template": null,
      "overrides": {}
    }

Example slotted profile:

    {
      "series": "T",
      "template": null,
      "overrides": {}
    }

The current New Channel command may override this per generated object instance.

### geometry.piercing.series

Series id for piercing/hole pattern mapping.

Examples:

    null
    T

Rules:

- `null` or empty means no default piercing.
- Non-empty string values must resolve against `mapping_hole_series.json`.
- Smoke tests validate non-null series ids.

### geometry.piercing.template

Reserved for future template-based piercing behavior.

Current records may use `null`.

### geometry.piercing.overrides

Reserved for future per-profile deviations from a mapped hole series.

Current records may use `{}`.

## finishes

List of finish codes available or expected for the profile.

Example:

    [
      "EG",
      "HG",
      "GR"
    ]

Current smoke tests require:

- `finishes` is a list.
- It is not empty.
- Every entry is a non-empty string.

The current workbench treats finish primarily as metadata.

## standard_lengths

Standard available lengths.

Example:

    {
      "ft": [10.0, 20.0],
      "m": [3.048, 6.096]
    }

Supported keys:

    ft
    m
    mm

Current smoke tests require at least one non-empty list among these keys.

All listed length values must be positive numeric values.

## mapping_hole_series.json

`mapping_hole_series.json` maps piercing series ids to concrete pattern metadata.

Current expected top-level structure:

    {
      "schema_version": "...",
      "hole_series": {
        "T": {
          "slot_pattern": {}
        }
      },
      "provenance": {}
    }

The schema smoke currently loads `hole_series`.

Older or alternate structures may use a top-level `series` object, but `hole_series` is the preferred contract.

## hole_series

The `hole_series` object maps series ids to records.

Example:

    {
      "T": {
        "slot_pattern": {
          "pitch_mm": 50.8,
          "slot_length_mm": 35.0,
          "slot_width_mm": 14.0
        }
      }
    }

## hole series record

A hole series record describes a reusable piercing pattern.

Current required field for slot-generating series:

    slot_pattern

## slot_pattern

A slot pattern currently requires:

    pitch_mm
    slot_length_mm
    slot_width_mm

### pitch_mm

Distance between repeated slot centers.

Must be positive numeric.

### slot_length_mm

Length of each slot.

Must be positive numeric.

### slot_width_mm

Width of each slot.

Must be positive numeric.

## fittings.json

`fittings.json` contains fitting records.

The fitting schema is intentionally separate from the profile schema.

Fitting records should not define channel-side piercing intent.

Add Fitting should consume fitting records and, in future workflows, may consume channel metadata such as `SlotCenters`.

## Generated FreeCAD channel objects

The New Channel command currently creates a `Part::Feature` with shape and metadata.

Known generated properties may include:

    UnistrutType
    ProfileId
    Finish
    Mode
    PiercingPreset
    HoleClearanceIn
    SlotCenters

## UnistrutType

Identifies the generated object type.

For channel profiles, this should be:

    profile

## ProfileId

Stores the source catalog profile id.

Example:

    P1000

This should remain the catalog id even when the generated object uses an instance-level piercing override.

## Finish

Stores finish code metadata.

Example:

    EG

## Mode

Stores the channel mode used at creation time.

## PiercingPreset

Stores the selected piercing preset from the New Channel UI.

Current possible values:

    __profile__
    __plain__
    T

Meaning:

    __profile__   use profile default
    __plain__     force plain/solid for this instance
    T             force T slotted pattern for this instance

## HoleClearanceIn

Stores hole/clearance metadata entered at channel creation time.

This is currently metadata only.

It does not yet drive fitting validation, fastener selection, or slot geometry.

## SlotCenters

List of FreeCAD vectors identifying computed slot center locations.

Rules:

- Generated from the active piercing series.
- Empty for plain/solid channels.
- Empty when no usable slot pattern exists.
- Used as metadata for future workflows.
- Not an assembly constraint system.

## Generated fitting objects

Generated fitting object metadata is intentionally separate from channel metadata.

Fitting objects should not redefine channel piercing state.

## Schema smoke contract

Schema smoke tests are no-FreeCAD tests.

They should catch catalog/data mistakes before GUI commands or FreeCAD geometry generation encounter them.

Current profile smoke responsibilities:

- Required profile fields
- Required geometry fields
- Numeric millimeter dimensions
- Positive gauge values
- Finish list sanity
- Standard length sanity
- Lipped U-channel profile spec sanity
- Piercing series resolution against `mapping_hole_series.json`
- Usable slot pattern metadata for mapped piercing series

Current fitting smoke responsibilities:

- Required fitting fields
- Basic fitting schema sanity

## Data model principles

### Records should be explicit

Avoid implicit behavior hidden in command code when a catalog field can express it clearly.

### Catalog default is not instance intent

A profile record describes the default catalog state.

A generated FreeCAD object may store user-selected authoring intent that differs from the default.

### Keep JSON schema checkable

Prefer simple object/list/string/number structures that can be validated without importing FreeCAD.

### Do not overfit to one profile

Profile and hole-series records should support catalog expansion without special-casing one part number in command code.

### Preserve future migration paths

Reserved fields such as `template` and `overrides` are allowed, but should remain simple until there is a real implementation need.
