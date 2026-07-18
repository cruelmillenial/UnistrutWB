# UnistrutWB Testing Policy

This document defines the current testing layers for UnistrutWB and the boundary between catalog validation and FreeCAD-dependent runtime testing.

The immediate goal is to catch data and schema mistakes early without requiring FreeCAD.

The longer-term goal is to add focused FreeCAD integration tests without making lightweight catalog checks depend on a FreeCAD installation or GUI environment.

## Testing layers

UnistrutWB uses, or is expected to use, several distinct testing layers.

| Layer | Current status | Requires FreeCAD | Purpose |
|---|---|---:|---|
| Catalog/schema smoke | Implemented | No | Validate JSON structure, required fields, types, values, and cross-file references. |
| Pure Python logic tests | Future | No | Validate deterministic helper logic that does not depend on FreeCAD. |
| FreeCAD object integration tests | Future | Yes | Create generated objects and verify documented properties and basic runtime behavior. |
| Geometry integration tests | Future | Yes | Verify shape creation, dimensions, piercing, and topology-level expectations. |
| Placement integration tests | Future | Yes | Verify initial fitting and channel placement behavior. |
| GUI workflow tests | Future | Yes, with GUI | Exercise dialogs, selections, and command interactions. |
| Assembly or solver tests | Out of current scope | Yes | Validate behavior owned by a future assembly integration or external workbench. |

These layers should remain separate.

A failure in a FreeCAD-dependent test must not prevent developers from running catalog/schema smoke tests in an ordinary Python environment.

## Current schema smoke tests

Current schema smoke scripts live under:

    scripts/smoke_profiles_schema.py
    scripts/smoke_fittings_schema.py
    scripts/smoke_all_schema.py

The combined entry point is:

    python3 scripts/smoke_all_schema.py

These scripts must remain runnable without importing FreeCAD.

### Purpose

Schema smoke tests validate catalog and mapping data before GUI commands or geometry builders consume it.

They are intended to catch mistakes such as:

- missing required fields
- invalid field types
- empty required values
- invalid numeric ranges
- malformed lists or objects
- unsupported enumerated values
- broken references between data files
- unusable piercing-pattern definitions
- inconsistent catalog structures

Schema smoke tests should fail with a clear message identifying the affected record and field whenever practical.

### Profile schema responsibilities

Profile smoke tests may validate:

- required profile fields
- unique profile identifiers
- required geometry fields
- numeric dimensions
- positive dimensions and gauge values
- finish-list structure
- standard-length structure
- supported profile specification kinds
- lipped U-channel profile data
- piercing-series references
- hole-series mapping structure
- usable slot-pattern metadata

### Fitting schema responsibilities

Fitting smoke tests may validate:

- required fitting fields
- unique fitting identifiers
- required geometry values
- supported fitting geometry types
- dimensional field types and ranges
- hole-count and hole-diameter metadata
- placement-policy structure
- supported placement modes
- allowed face-class values
- slot-policy values
- mate-frame record structure
- hardware-preset field structure

The exact checks should reflect fields that are part of the documented catalog contract.

## Generated-object metadata contracts

Generated channel and fitting property contracts are documented in:

    docs/DATA_MODEL.md

Examples include:

- `UnistrutType`
- `ProfileId`
- `FittingId`
- `Length`
- `Finish`
- `PiercingPreset`
- `SlotCenters`
- `HostProfile`
- `MateFrames`
- `MateFrameMetadata`

Catalog smoke tests may validate that source records contain the information needed to produce these properties.

Catalog smoke tests cannot prove that the FreeCAD commands actually create those properties correctly.

Verifying generated FreeCAD object properties requires a future FreeCAD object integration test layer.

## No-FreeCAD boundary

A test belongs in catalog/schema smoke when it can be answered entirely from repository data and deterministic Python logic.

Examples:

- Does every profile have a unique id?
- Is a referenced piercing series present?
- Is `slot_width_mm` positive?
- Does a fitting placement policy use a supported value?
- Is a mate-frame record structurally complete?

A test does not belong in catalog/schema smoke when it requires:

- importing `FreeCAD`
- importing `Part`
- creating a `Document`
- creating a `Part::Feature`
- building a shape
- examining topology
- using `Placement`
- accessing GUI selection
- opening a dialog
- rendering an object

Those checks belong in a FreeCAD-dependent integration layer.

## Pure Python logic tests

Deterministic helper code should remain independent of FreeCAD where practical.

Pure Python tests are appropriate for functions such as:

- catalog lookup
- unit conversion
- piercing-series resolution
- selection-policy interpretation
- metadata normalization
- validation helpers
- BOM grouping logic
- cut-list calculations

Separating deterministic logic from FreeCAD adapters makes that logic easier to test and reuse.

Do not move FreeCAD-specific behavior into pure Python modules solely to satisfy a testing preference. The separation should reflect a real architectural boundary.

## Future FreeCAD object integration tests

A future FreeCAD integration test layer should run inside, or through, a FreeCAD Python environment.

Its first responsibility should be verifying the generated-object metadata contracts documented in `docs/DATA_MODEL.md`.

Candidate channel checks include:

- New Channel creates a `Part::Feature`.
- `UnistrutType` equals `profile`.
- `ProfileId` preserves catalog identity.
- `Length` matches the authored length.
- `Finish`, `Mode`, and `PiercingPreset` preserve authoring choices.
- plain channels have an empty `SlotCenters` list.
- supported slotted channels produce expected slot-center metadata.

Candidate fitting checks include:

- Add Fitting creates a `Part::Feature`.
- `UnistrutType` equals `fitting`.
- `FittingId` preserves catalog identity.
- catalog-derived metadata is copied when present.
- selected hole diameter is stored correctly.
- unplaced fittings have an empty `HostProfile`.
- mate-frame properties are created and serializable.
- initial placement behavior matches the supported placement policy.

These tests should check documented behavior rather than incidental implementation details.

## Geometry integration tests

Geometry tests require FreeCAD and should be separate from schema smoke.

Candidate checks include:

- shape creation succeeds
- shape is non-null
- shape is valid
- bounding dimensions are within tolerance
- profile wall thickness is represented correctly
- requested slots or holes are present
- plain channels remain unpierced
- supported fitting builders produce expected gross dimensions

Geometry tests should use explicit tolerances.

They should avoid relying on unstable face or edge numbering unless a stable topology contract is deliberately introduced.

## Placement integration tests

Placement tests should verify initial authoring behavior, not claim to verify persistent assembly relationships.

Candidate checks include:

- unplaced objects receive the intended authoring offset
- selected host names are recorded correctly
- supported face classes are accepted
- unsupported placement modes are rejected
- nearest-slot policy chooses the expected reference point
- picked-point policy preserves the intended point
- initial fitting orientation is reasonable for the selected face

Current placement metadata and `Placement` values are not Assembly constraints.

## GUI testing

GUI automation is not required during the current phase.

Future GUI tests may cover:

- dialog fields
- combo-box options
- selection handling
- command registration
- cancel behavior
- invalid-input feedback
- object creation after dialog acceptance

GUI tests should not become the only coverage for logic that could instead be tested through pure Python or FreeCAD object integration tests.

## Assembly boundary

UnistrutWB is not currently an Assembly solver.

Current tests should not claim to verify:

- persistent mates
- solved mechanical relationships
- joint degrees of freedom
- automatic fitting-to-channel updates
- interference-free assembly
- fastener engagement
- structural adequacy

Mate frames, slot centers, host names, and object placement are reference and authoring metadata unless a future solver integration explicitly assigns stronger semantics.

## Why no FreeCAD-dependent metadata test is added in this phase

The current sprint establishes and documents generated-object metadata contracts.

It does not yet add a FreeCAD integration harness because doing so would require decisions about:

- supported FreeCAD versions
- headless execution
- module and workbench loading
- document lifecycle
- test isolation
- temporary files
- CI installation strategy
- GUI versus non-GUI execution
- geometry tolerances
- failure reporting

Those decisions deserve a discrete implementation task.

Adding an improvised FreeCAD-dependent check during this documentation sprint would risk coupling the project to an incomplete test runner.

The current decision is therefore:

- document the generated-object contracts now
- keep catalog smoke no-FreeCAD
- add FreeCAD integration testing as a separate future milestone

## Test design rules

Tests should be:

- deterministic
- repeatable
- explicit about ownership boundaries
- fast enough for their intended layer
- clear when they fail
- focused on documented contracts
- independent of network access
- independent of catalog ordering unless ordering is itself contractual

Tests should not depend on:

- local absolute paths
- object creation order unless documented
- viewer state
- unspecified defaults
- incidental face numbering
- live catalog websites
- external services

## Change policy

When changing catalog data:

1. Run the relevant schema smoke test.
2. Run the combined schema smoke test.
3. Add or update schema checks when introducing a new required field or constrained value.
4. Update `docs/DATA_MODEL.md` when the data contract changes.

When changing generated FreeCAD metadata:

1. Update `docs/DATA_MODEL.md`.
2. Determine whether catalog smoke needs new source-data checks.
3. Add or update FreeCAD integration coverage once that test layer exists.
4. Do not add FreeCAD imports to existing schema smoke scripts.

When changing geometry or placement behavior:

1. Keep schema validation limited to the source-data contract.
2. Add FreeCAD-dependent coverage in the appropriate future integration layer.
3. Update architecture documentation if command ownership or subsystem boundaries change.

## Current required checks before commit

For catalog, metadata-documentation, and schema changes, run:

    python3 scripts/smoke_all_schema.py
    git diff --check

Review the relevant diff before committing.

Where a change affects only documentation, the schema smoke still serves as a quick repository sanity check, but it does not validate prose content.

## Future testing milestones

Likely future tasks include:

1. Define supported FreeCAD test versions.
2. Add a headless FreeCAD test entry point.
3. Add generated channel metadata integration checks.
4. Add generated fitting metadata integration checks.
5. Add basic geometry validity checks.
6. Add placement-policy integration checks.
7. Add CI execution for no-FreeCAD tests.
8. Add optional CI execution for FreeCAD-dependent tests.

These should be introduced incrementally rather than as one large test-harness project.
