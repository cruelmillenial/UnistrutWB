# Contributing to UnistrutWB

This document records the current working rules for developing UnistrutWB.

The project is early-stage, so the goal is disciplined incremental development rather than rapid feature sprawl.

## Core rule

Keep the workbench catalog-aware, schema-checked, and narrowly scoped.

UnistrutWB should create useful FreeCAD objects from catalog data. It should not become an assembly solver, structural analysis tool, fastener generator, or universal design assistant.

## Development workflow

Before starting work:

    git checkout dev
    git pull --ff-only origin dev
    git status

After making a change:

    python3 -m py_compile <changed python files>
    python3 scripts/smoke_all_schema.py
    git status
    git diff

Commit only after checks pass.

## Smoke tests

The combined smoke command is:

    python3 scripts/smoke_all_schema.py

This should pass before every commit that touches:

- Catalog data
- Schema smoke scripts
- Command code that consumes catalog data
- Geometry-builder behavior
- New Channel behavior
- Add Fitting behavior

Individual smoke scripts:

    python3 scripts/smoke_profiles_schema.py
    python3 scripts/smoke_fittings_schema.py

Smoke scripts must not require FreeCAD.

## Commit discipline

Prefer one logical change per commit.

Good commit examples:

    Add P1100 profile record
    Add New Channel piercing controls
    Validate profile piercing series mappings
    Offset new channels for viewer authoring

Avoid commits that mix unrelated work.

Bad mixed commit example:

    Add P1100, change fitting behavior, rewrite docs, tweak UI

## Branch discipline

Use `dev` as the active development branch unless a specific feature branch is needed.

Avoid force-pushing unless recovering from a known bad remote state and after deliberate review.

## File-editing discipline

Prefer normal source editing in an IDE or editor for non-trivial changes.

Small generated or mechanical edits are acceptable, but review the resulting diff before committing.

Do not rely on blind patch scripts when a human-readable edit is safer.

## Catalog expansion rules

When adding a profile record:

1. Add only the profile record unless the schema needs to change.
2. Run profile smoke.
3. Run combined smoke.
4. Create the profile in FreeCAD.
5. Visually sanity-check the result.
6. Commit the catalog addition by itself.

Minimum checks:

    python3 scripts/smoke_profiles_schema.py
    python3 scripts/smoke_all_schema.py

FreeCAD sanity check:

- The profile appears in the selector.
- The object creates without exceptions.
- Overall dimensions appear plausible.
- Piercing behavior matches the profile default or selected override.
- New object placement offset still works.

## Profile data rules

Profile records belong in:

    Mod/UnistrutWB/data/profiles.json

Profiles describe catalog defaults.

Profiles should not describe user-specific assembly decisions.

Required profile fields:

    id
    family
    gauge
    geometry
    finishes
    standard_lengths

Required geometry fields:

    width
    height
    thickness

For current lipped U-channel records, include:

    geometry.profile_spec.kind
    geometry.profile_spec.t.mm
    geometry.profile_spec.lip_return.mm

Use:

    "kind": "u_channel_lipped"

for currently supported lipped channel profiles.

## Piercing data rules

Piercing belongs to channel/profile data and New Channel authoring behavior.

It does not belong to Add Fitting.

Profile records may define catalog default piercing:

    "piercing": {
      "series": "T",
      "template": null,
      "overrides": {}
    }

Plain profiles should use:

    "piercing": {
      "series": null,
      "template": null,
      "overrides": {}
    }

Non-null `series` values must resolve against:

    Mod/UnistrutWB/data/mapping_hole_series.json

The profile smoke test should catch invalid series references.

## Hole-series mapping rules

Hole-series mappings belong in:

    Mod/UnistrutWB/data/mapping_hole_series.json

Preferred top-level mapping key:

    hole_series

Slot-generating series should include a usable `slot_pattern`.

Current required slot pattern fields:

    pitch_mm
    slot_length_mm
    slot_width_mm

All must be positive numeric values.

## New Channel rules

New Channel owns channel-side authoring intent.

It may handle:

- Profile choice
- Length
- Finish
- Mode
- Piercing preset
- Hole/clearance metadata
- Slot center metadata
- Viewer-authoring placement offset

New Channel should not create assembly constraints.

New Channel should not create fasteners.

New Channel should not mutate catalog records.

When New Channel applies a piercing override, it should apply that override before geometry generation.

## Add Fitting rules

Add Fitting owns fitting creation.

It should not own:

- Channel piercing selection
- Channel hole pattern selection
- Channel catalog defaults
- Assembly solving
- Fastener generation

Future Add Fitting behavior may consume channel metadata, such as `SlotCenters`, but should not redefine channel-side state.

## Viewer placement rules

Automatic offset placement for newly created channels is a viewer-authoring convenience.

It is allowed because it prevents newly created objects from hiding each other at the origin.

It must not be treated as:

- Assembly intent
- A mate
- A constraint
- A structural relationship
- Final design placement

## Assembly boundary

Final spatial relationships belong outside simple object-creation commands.

Assembly Workbench or another dedicated workflow should own:

- Mates
- Constraints
- Alignment semantics
- Final object placement
- Design intent between separate parts

UnistrutWB may provide metadata that helps those workflows later.

## Fastener boundary

Fastener generation and detailed fastener selection should remain outside UnistrutWB unless a future integration is deliberately designed.

FreeCAD Fasteners Workbench or a similar tool should own:

- Bolt geometry
- Nut geometry
- Washer geometry
- Threaded fastener details

UnistrutWB may store metadata useful to such tools.

## Documentation rules

When a design decision becomes repeated or load-bearing, document it.

Good candidates for documentation:

- Data model changes
- JSON schema changes
- New object properties
- Command ownership boundaries
- Workflow assumptions
- Non-goals

Do not wait until the catalog is large to document schema assumptions.

## Issue discipline

Use issues for bounded work.

Good issue scope:

- Add two low-risk profile records.
- Validate piercing mappings in schema smoke.
- Add New Channel piercing controls.
- Document data model v1.

Poor issue scope:

- Make fittings smart.
- Add all Unistrut parts.
- Implement assemblies.
- Fix everything about piercing.

Close issues only after:

- Code is committed.
- Relevant smoke tests pass.
- Any required FreeCAD sanity check is done.
- The issue acceptance criteria are satisfied.

## Definition of done

For code changes:

- Python files compile.
- Combined smoke passes.
- FreeCAD sanity check passes if GUI or geometry behavior changed.
- Diff is reviewed.
- Commit is pushed.

For catalog changes:

- Schema smoke passes.
- Combined smoke passes.
- New records appear in FreeCAD.
- Visual sanity check passes.
- No unrelated files are changed.

For documentation changes:

- Markdown is readable.
- It reflects current architecture.
- It does not promise unimplemented behavior as complete.
- It captures boundaries and decisions clearly.

## Development philosophy

Prefer boring guardrails over clever recovery.

Prefer explicit metadata over hidden assumptions.

Prefer narrow commands over god-commands.

Prefer schema validation before catalog expansion.

Prefer catalog truth plus instance authoring intent over mutating source records.

Prefer small, passing increments over large speculative rewrites.

The workbench should become harder to break as it grows.
