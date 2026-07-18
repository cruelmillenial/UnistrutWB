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

## Generated channel object metadata contract

The New Channel command creates a `Part::Feature` from a profile catalog record plus instance-level authoring choices.

The generated object is not the catalog record itself. It is a specific authored instance created from catalog data.

Generated channel metadata falls into five broad categories:

| Category | Meaning |
|---|---|
| Catalog identity | Identifies the source catalog record. |
| Instance authoring intent | Captures choices made while creating this object. |
| Derived metadata | Computed from catalog data and/or instance intent. |
| BOM/cut-list metadata | Supports quantity, finish, length, and fabrication summaries. |
| Downstream reference metadata | Supports future tools without acting as a constraint or solver. |

### Expected generated properties

| Property | FreeCAD type | Category | Meaning |
|---|---|---|---|
| `UnistrutType` | `App::PropertyString` | Catalog identity | Identifies the object as a generated channel profile. Current value: `profile`. |
| `ProfileId` | `App::PropertyString` | Catalog identity | Stores the source profile id from `profiles.json`. |
| `Length` | `App::PropertyLength` | BOM/cut-list metadata | Stores the authored channel length. |
| `Finish` | `App::PropertyString` | BOM/cut-list metadata | Stores the selected finish code. |
| `Mode` | `App::PropertyString` | Instance authoring intent | Stores the channel-generation mode selected at creation time. |
| `PiercingPreset` | `App::PropertyString` | Instance authoring intent | Stores the selected piercing behavior for this instance. |
| `HoleClearanceIn` | `App::PropertyString` | Instance authoring intent | Stores user-entered hole or clearance metadata in inches. |
| `SlotCenters` | `App::PropertyVectorList` | Derived metadata / downstream reference metadata | Stores computed slot-center vectors for the active piercing pattern. |

### `UnistrutType`

`UnistrutType` identifies the broad generated object kind.

For generated channel objects, the current value is:

    profile

Downstream tools may use this property to distinguish channel profiles from fittings and other workbench objects.

### `ProfileId`

`ProfileId` stores the source profile id from `profiles.json`.

Examples:

    P1000
    P1100
    P4000
    P4100

`ProfileId` remains the catalog identity even when the generated object uses an instance-level piercing override.

For example, a generated `P1000` object may use `T` piercing while still retaining:

    ProfileId = P1000

The source profile identity and the authored piercing intent are separate concepts.

### `Length`

`Length` stores the channel length selected when the object is created.

It is currently stored as an `App::PropertyLength` and is expected to be the canonical generated-object length value for future BOM and cut-list workflows.

### `Finish`

`Finish` stores the selected finish code.

Example:

    EG

Finish is currently metadata and is expected to be consumed by future BOM and cut-list workflows.

### `Mode`

`Mode` stores the channel-generation mode selected in the New Channel command.

Current values include:

    simple
    detailed

This is instance authoring metadata.

It is not assembly placement intent.

### `PiercingPreset`

`PiercingPreset` stores the piercing option selected when the channel is generated.

Current values:

    __profile__
    __plain__
    T

Meanings:

| Value | Meaning |
|---|---|
| `__profile__` | Use the source profile's catalog-default piercing state. |
| `__plain__` | Force plain/solid behavior for this generated instance. |
| `T` | Force T-slotted behavior for this generated instance. |

`PiercingPreset` describes instance authoring intent.

It does not mutate the source profile record.

### `HoleClearanceIn`

`HoleClearanceIn` stores hole or clearance metadata entered during channel creation.

It is currently stored as string metadata.

It does not yet drive:

- slot geometry
- fitting validation
- fastener selection
- assembly constraints

Future fitting, fastener, or BOM workflows may consume it once those workflows are deliberately designed.

### `SlotCenters`

`SlotCenters` stores computed FreeCAD vectors for the active piercing pattern.

Slot centers are derived from:

- the active piercing series
- the hole-series mapping
- the generated channel length
- the channel geometry

Rules:

- Plain or solid channels validly have an empty list.
- Channels without a usable slot pattern validly have an empty list.
- The values are generated metadata, not separately authored inputs.
- Future tools may consume them as reference locations.

`SlotCenters` is not:

- an assembly constraint system
- a mate
- a final placement rule
- structural validation
- proof that a fitting or fastener is valid

### Catalog truth vs instance intent

Generated channel objects preserve both catalog identity and instance authoring intent.

These answer different questions:

| Question | Property |
|---|---|
| What catalog profile did this object come from? | `ProfileId` |
| What length and finish were authored for this object? | `Length`, `Finish` |
| What generation behavior did the user select? | `Mode`, `PiercingPreset`, `HoleClearanceIn` |
| What reference data was derived from those choices? | `SlotCenters` |

Do not collapse these concepts into one property.

Catalog records describe defaults.

Generated object properties describe a specific authored instance.

### Downstream expectations

Downstream workflows may rely on documented properties only.

Current safe expectations:

- `UnistrutType` identifies the generated object kind.
- `ProfileId` identifies the source profile.
- `Length` and `Finish` are canonical generated-object BOM inputs.
- `Mode`, `PiercingPreset`, and `HoleClearanceIn` preserve authoring intent.
- `SlotCenters` provides derived reference locations.

Downstream workflows should not infer behavior from viewer placement, object ordering, or undocumented properties.

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
