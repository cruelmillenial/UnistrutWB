# UnistrutWB

A catalog-aware FreeCAD workbench for authoring Unistrut-style channel and fitting objects from normalized JSON data.

## Current MVP direction

UnistrutWB is not intended to be a full assembly solver.

The project boundary is:

```text
UnistrutWB = normalized catalog datastore + CAD object factory + metadata/BOM layer
FreeCAD Assembly = final spatial relationships / mating / constraints
FreeCAD Fasteners = bolts, nuts, washers, and standard hardware geometry
```

The workbench should create useful, metadata-rich CAD objects that can be refined, constrained, assembled, and documented using other FreeCAD workbenches.

## Project documentation

The current architecture and contribution rules are captured in:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — product boundary, command ownership, New Channel / Add Fitting split, piercing model, and SlotCenters intent.
- [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) — catalog datastore structure, profile/fitting record expectations, generated-object metadata, and schema smoke references.
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) — development workflow, smoke-test discipline, commit discipline, and catalog expansion rules.
- [`docs/assembly_reference_schema.md`](docs/assembly_reference_schema.md) — Assembly-facing reference geometry and mate-frame concepts.
- [Testing policy](docs/TESTING.md)

## Schema smoke tests

Before expanding profile or fitting catalog records, run the combined no-FreeCAD schema smoke check from the repository root:

```bash
python3 scripts/smoke_all_schema.py
```

This command runs the current Phase 1 datastore checks:

```bash
python3 scripts/smoke_fittings_schema.py
python3 scripts/smoke_profiles_schema.py
```

These schema smoke tests are pure Python validation utilities. They do not require FreeCAD, do not launch the workbench, and should pass before catalog breadth is expanded.

Schema smoke utilities live under `scripts/`. Do not reference `tests/` for these commands unless the project later adopts a separate test-runner layout.

## Profile expansion checklist

Do not add a new production profile record until `python3 scripts/smoke_all_schema.py` passes.

Minimum record checklist:

- `id`: catalog/profile identifier.
- `family`: catalog-facing family bucket.
- `gauge`: positive gauge value.
- `geometry`: width, height, and thickness with numeric `mm` values.
- `geometry.profile_spec`: shape-builder contract such as `u_channel_lipped`, including required dimensions like `t.mm` and `lip_return.mm`.
- `finishes`: non-empty list of finish codes.
- `standard_lengths`: at least one non-empty length list.
- `provenance`: catalog/source notes when available.
- Combined smoke runner passes after the edit.

See [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) and [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for fuller profile rules and catalog-expansion workflow.

## Fitting expansion checklist

Do not add a new Phase 1 fitting record until `python3 scripts/smoke_all_schema.py` passes.

Minimum record checklist:

- `id`, `name`, `category`, `display_group`, and `variant_label`.
- `family_id`: product/family bucket.
- `geometry_type`: shape-builder discriminator.
- `type`: retained only as a legacy fallback during Phase 1; keep it aligned with `geometry_type` until the fallback is removed.
- `hole_diameter_options_in` and `default_hole_diameter_in`, with default included in options.
- `hardware_preset` or equivalent metadata for later BOM/Fasteners handoff.
- `placement`: supported modes, allowed face classes, and slot policy.
- `anchor`: local-origin convention.
- `orientation`: default orientation policy.
- `mate_frames`: Assembly-facing reference metadata with `id`, `kind`, and `role`.
- `provenance`: catalog/source notes when available.
- Combined smoke runner passes after the edit.

See [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) and [`docs/assembly_reference_schema.md`](docs/assembly_reference_schema.md) for fuller fitting and reference-metadata details.

## Current capabilities

The current development branch supports:

- Creating Unistrut channel profiles from JSON data
- Current profile records: `P4100`, `P4000`, `P1000`, and `P1100`
- Generating slotted or plain/solid channel instances from catalog profiles
- New Channel piercing controls: `Profile default`, `Plain / solid`, and `T slotted`
- Recording generated-channel metadata such as `PiercingPreset`, `HoleClearanceIn`, and `SlotCenters`
- Offsetting newly created channel objects for easier viewer-authoring inspection
- Generating slot centers on channel objects when the active piercing pattern supports them
- Adding catalog-aware fitting objects
- Current fitting records: `P1065` and `DEV_ANGLE_90_2LEG`
- Grouping fittings by category and variant in the Add Fitting dialog
- Selecting hole diameter presets during fitting creation
- Attaching catalog metadata and mate-frame metadata to generated fitting objects
- Rough face-based fitting placement as an authoring convenience
- Creating unplaced fitting objects when no valid host face is selected
- Exporting a basic BOM / cut list CSV

## Current data model

The workbench uses split JSON datastore files under:

```text
Mod/UnistrutWB/data/
```

Important files include:

```text
profiles.json
fittings.json
finishes.json
mapping_hole_series.json
notes_derating.json
```

Current fitting records include metadata such as:

```text
id
name
category
display_group
variant_label
family_id
type
geometry_type
hole_count
hole_diameter_options_in
default_hole_diameter_in
hardware_preset
placement
anchor
orientation
mate_frames
```

The detailed datastore contract lives in [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md).

## New Channel workflow

The New Channel command creates channel objects from `profiles.json`.

Current flow:

1. Choose a profile, such as `P4100`, `P4000`, `P1000`, or `P1100`.
2. Choose length, finish, and mode metadata.
3. Choose piercing behavior:
   - `Profile default`
   - `Plain / solid`
   - `T slotted`
4. Create the generated channel object.

Piercing selection is applied before channel geometry generation. This means the generated object can preserve catalog identity while carrying instance-level authoring intent.

For example, a catalog-default plain profile can still generate a slotted instance while preserving `ProfileId`.

## Add Fitting workflow

The Add Fitting dialog is moving toward catalog object authoring rather than final assembly placement.

Current flow:

1. Choose a fitting category, such as `Splice Plates` or `Angle Brackets`.
2. Choose a fitting variant, such as `2-Hole Splice Plate`.
3. Choose a hole diameter preset.
4. Create the fitting object.

If a valid channel face is selected, Add Fitting may place the fitting roughly using the current placement policy.

If no valid placement selection exists, the fitting is created unplaced as a catalog object so it can later be moved or constrained using Assembly.

## Placement policy

Current placement logic is intentionally limited.

The workbench distinguishes simple face classes such as:

```text
open_face
z_face
y_face
```

For current Phase 1 fitting tests:

- `P1065` is treated as an open/channel-nut-side splice plate.
- `DEV_ANGLE_90_2LEG` is treated as a provisional angle bracket.
- Open-face placement can snap to channel slot centers.
- Non-open z-face placement uses the picked point.
- Unsupported face or edge selections reject honestly.

This placement layer is an authoring convenience, not the final assembly engine.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the command-boundary explanation.

## Assembly strategy

FreeCAD Assembly is expected to own final positioning and constraints.

UnistrutWB should expose clean geometry, stable origins, useful metadata, and reference/mate-frame information.

The goal is to make generated UnistrutWB objects Assembly-friendly without turning UnistrutWB into an Assembly solver.

See [`docs/assembly_reference_schema.md`](docs/assembly_reference_schema.md) for the current Assembly-facing reference schema.

## Fasteners strategy

UnistrutWB should not custom-model standard fasteners.

Instead, fitting records should carry hardware metadata such as thread / bolt size, channel nut type, washer requirements, hardware preset, and BOM line items.

Fastener geometry should be handled later through FreeCAD Fasteners or compatible tooling.

## Development install

During development, symlink or copy the workbench into your FreeCAD Mod directory.

Example Linux Snap-style development layout:

```bash
~/src/UnistrutWB/Mod/UnistrutWB
~/snap/freecad/common/Mod/UnistrutWB -> ~/src/UnistrutWB/Mod/UnistrutWB
```

Restart FreeCAD after code changes unless using manual module reloads.

## Quick smoke test

1. Open FreeCAD.
2. Switch to the `UnistrutWB` workbench.
3. Use `New Channel` to create a `P4100` channel.
4. Confirm piercing controls are available.
5. Create a channel using `Profile default`, `Plain / solid`, or `T slotted`.
6. Use `Add Fitting`.
7. Confirm the dialog shows fitting categories and variants.
8. Create a `P1065` splice plate or `DEV_ANGLE_90_2LEG` angle bracket.
9. Select the generated fitting and confirm catalog metadata appears in the property panel.
10. Use FreeCAD Assembly for final placement or constraint experiments.

## Current roadmap

Near-term priorities:

- Keep Add Fitting focused on catalog object authoring.
- Keep New Channel responsible for channel-side piercing authoring intent.
- Keep schema guardrails passing before adding catalog breadth.
- Improve object metadata expectations and smoke coverage where possible.
- Improve BOM/export fidelity.
- Normalize more catalog records under schema guardrails.
- Add more fitting families and variants only after data contracts remain stable.
- Document placement as convenience-level, not solver-level.

Non-goals for MVP:

- Full Unistrut assembly solving inside UnistrutWB
- Multi-channel splice-joint inference
- Bolt stack solving
- Fastener geometry generation from scratch
- One-click final mechanical placement

## Project status

This project is under active development on the `dev` branch.

The current MVP direction is:

```text
catalog normalization -> CAD object generation -> metadata/BOM -> Assembly/Fasteners integration
```
