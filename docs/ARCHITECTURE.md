# UnistrutWB Architecture

UnistrutWB is a FreeCAD workbench for catalog-aware Unistrut-style channel and fitting authoring.

The workbench is responsible for creating useful, metadata-bearing FreeCAD objects from catalog records. It is not an assembly solver, mating system, structural analysis tool, or fastener generator.

## Current architectural boundary

UnistrutWB owns:

- Catalog-backed channel profile creation
- Catalog-backed fitting creation
- Basic generated geometry
- Object metadata needed by later workflows
- Schema smoke tests for catalog records
- Viewer-authoring conveniences that make objects easier to inspect

UnistrutWB does not own:

- Final assembly constraints
- Mechanical mating semantics
- Structural load validation
- Fastener geometry
- Bolt/nut/washer selection
- Procurement correctness
- Exhaustive catalog completeness

Those responsibilities are expected to remain outside the workbench or be delegated to other FreeCAD workbenches.

## Major components

    User
     |
     v
    FreeCAD GUI Commands
     |
     +-- New Channel
     |    |
     |    v
     |   profiles.json
     |    |
     |    v
     |   Channel geometry builder
     |    |
     |    v
     |   Part::Feature object
     |
     +-- Add Fitting
          |
          v
         fittings.json
          |
          v
         Fitting geometry builder
          |
          v
         Part::Feature object

## Generated-object metadata boundary

Catalog records are source inputs used by UnistrutWB commands to create geometry and metadata-bearing FreeCAD objects.

The catalog files remain the source of product defaults and reusable definitions:

- `profiles.json` defines channel profile records.
- `fittings.json` defines fitting records.
- mapping files define reusable supporting data such as piercing patterns.

Generated FreeCAD object properties are runtime document metadata for a specific authored instance.

They may preserve:

- source catalog identity
- user-selected authoring intent
- catalog-derived descriptive values
- derived reference metadata
- current placement state
- future workflow reference intent

Catalog records and generated object properties are related but are not interchangeable.

A generated object may preserve its source catalog identity while also recording instance choices that differ from the catalog default.

Downstream workflows should rely only on generated-object properties that are explicitly documented in `docs/DATA_MODEL.md`.

They should not infer behavior from:

- object names alone
- document ordering
- viewer offsets
- undocumented properties
- current visual coincidence between objects

Generated metadata may support future BOM, placement, inspection, fastener, or assembly workflows.

It does not itself create:

- persistent Assembly constraints
- solved mates
- structural validation
- automatic fastener selection
- guaranteed mechanical compatibility

UnistrutWB creates catalog-aware authoring objects and reference metadata. It is not an Assembly solver.

## New Channel command

The New Channel command creates channel profile objects from `profiles.json`.

It currently handles:

- Profile selection
- Length
- Finish metadata
- Mode
- Piercing preset
- Hole/clearance metadata
- Slot center metadata
- Viewer offset placement for authoring convenience

Generated channel objects may include:

- `UnistrutType`
- `ProfileId`
- `Finish`
- `Mode`
- `PiercingPreset`
- `HoleClearanceIn`
- `SlotCenters`

The New Channel command owns channel-side authoring intent.

That means a catalog profile can describe its default state, while the user can still create an instance with a different authoring choice such as plain/solid or T-slotted.

## Piercing model

Piercing is channel-side metadata and geometry behavior.

The active rule is:

- `Profile default` obeys the catalog profile record.
- `Plain / solid` suppresses piercing for the generated channel instance.
- `T slotted` forces the T slot pattern for the generated channel instance.

The selected piercing mode affects channel geometry before the channel shape is built.

This distinction matters because the shape must be generated from the intended piercing state. Changing only metadata after shape generation is not sufficient.

## SlotCenters

`SlotCenters` is metadata derived from the active piercing pattern.

It is intended to support later workflows such as fitting placement, inspection, or alignment helpers.

`SlotCenters` is not an assembly constraint system.

A channel can validly have no slot centers when it is plain/solid or when its profile has no usable slot pattern.

## Add Fitting command

The Add Fitting command creates fitting objects from `fittings.json`.

It should remain focused on fitting creation.

It should not own channel piercing selection, channel hole pattern selection, or channel authoring decisions.

Future fitting workflows may consume channel metadata such as `SlotCenters`, but should not redefine channel catalog state.

## Viewer authoring offset

Newly created channel objects are offset in the document so repeated authoring does not create multiple objects directly on top of each other.

This is a viewer-authoring convenience only.

It is not:

- Assembly intent
- A mate
- A constraint
- A placement rule for final designs
- A structural relationship

Final positioning belongs to the user or to an assembly workflow.

## Catalog data flow

    profiles.json
       |
       v
    profile selection
       |
       v
    optional instance piercing override
       |
       v
    geometry builder
       |
       v
    FreeCAD object + metadata

    fittings.json
       |
       v
    fitting selection
       |
       v
    fitting geometry builder
       |
       v
    FreeCAD object + metadata

## Smoke test flow

    scripts/smoke_all_schema.py
       |
       +-- scripts/smoke_profiles_schema.py
       |
       +-- scripts/smoke_fittings_schema.py

Profile schema smoke validates:

- Required profile fields
- Required geometry fields
- Numeric dimensions
- Gauge sanity
- Finish list sanity
- Standard length sanity
- Lipped U-channel profile specs
- Piercing series references against `mapping_hole_series.json`

Fitting schema smoke validates fitting records without requiring FreeCAD.

The smoke scripts are intended to catch catalog and schema mistakes before FreeCAD geometry generation.

## Design principles

### Catalog truth and authoring intent are different

Catalog records describe known product defaults.

User choices in the GUI describe authoring intent for a generated object instance.

A generated object may therefore differ from the profile default while still preserving the original `ProfileId`.

### Keep commands narrow

New Channel owns channel creation.

Add Fitting owns fitting creation.

Do not turn Add Fitting into a universal workflow manager.

### Avoid assembly semantics in authoring commands

Object creation commands may create geometry and metadata, but they should not claim to solve final relationships between objects.

### Prefer guardrails before expansion

When adding catalog records, add or improve schema checks before large-scale expansion.

### Metadata should support future workflows

Generated metadata should be explicit, inspectable, and useful to future tools.

It should not require hidden assumptions in command code.

## Current project state

The workbench currently has a small seed catalog and enough schema protection to continue expansion safely.

Known supported profile behavior includes:

- Plain lipped U-channel geometry
- T-style slotted geometry where mapped
- Instance-level piercing override through New Channel
- Slot center metadata generation

The next major stabilization step is to document the data contracts and continue hardening schema checks before broad catalog expansion.
