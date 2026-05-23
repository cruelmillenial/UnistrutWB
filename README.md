# UnistrutWB

A catalog-aware FreeCAD workbench for authoring Unistrut-style channel and fitting objects from normalized JSON data.

## Current MVP direction

UnistrutWB is not intended to be a full assembly solver.

The project boundary is:

UnistrutWB = normalized catalog datastore + CAD object factory + metadata/BOM layer
FreeCAD Assembly = final spatial relationships / mating / constraints
FreeCAD Fasteners = bolts, nuts, washers, and standard hardware geometry

The workbench should create useful, metadata-rich CAD objects that can be refined, constrained, assembled, and documented using other FreeCAD workbenches.

Current capabilities

The current development branch supports:

Creating Unistrut channel profiles from JSON data
Generating slot centers on channel objects
Adding catalog-aware fitting objects
Grouping fittings by category and variant in the Add Fitting dialog
Selecting hole diameter presets during fitting creation
Attaching catalog metadata to generated fitting objects
Rough face-based fitting placement as an authoring convenience
Creating unplaced fitting objects when no valid host face is selected
Exporting a basic BOM / cut list CSV
Current data model

The workbench uses split JSON datastore files under:

Mod/UnistrutWB/data/

Important files include:

profiles.json
fittings.json
finishes.json
mapping_hole_series.json
notes_derating.json

Current fitting records include metadata such as:

id
name
category
display_group
variant_label
family_id
type
hole_count
hole_diameter_options_in
default_hole_diameter_in
hardware_preset
placement
anchor
orientation
mate_frames

Add Fitting workflow

The Add Fitting dialog is moving toward catalog object authoring rather than final assembly placement.

Current flow:

Choose a fitting category, such as Splice Plates or Angle Brackets.
Choose a fitting variant, such as 2-Hole Splice Plate.
Choose a hole diameter preset.
Create the fitting object.

If a valid channel face is selected, Add Fitting may place the fitting roughly using the current placement policy.

If no valid placement selection exists, the fitting is created unplaced as a catalog object so it can later be moved or constrained using Assembly.

Placement policy

Current placement logic is intentionally limited.

The workbench distinguishes simple face classes such as:

open_face
z_face
y_face

For current Phase 1 fitting tests:

P1065 is treated as an open/channel-nut-side splice plate.
DEV_ANGLE_90_2LEG is treated as a provisional angle bracket.
Open-face placement can snap to channel slot centers.
Non-open z-face placement uses the picked point.
Unsupported face or edge selections reject honestly.

This placement layer is an authoring convenience, not the final assembly engine.

Assembly strategy

FreeCAD Assembly is expected to own final positioning and constraints.

UnistrutWB should expose clean geometry, stable origins, useful metadata, and eventually reference/mate-frame information for objects such as:

channel longitudinal axis
open-face plane
slot centerline
slot centers
end planes
fitting mounting faces
fitting hole centers / axes

The goal is to make generated UnistrutWB objects Assembly-friendly.

Fasteners strategy

UnistrutWB should not custom-model standard fasteners.

Instead, fitting records should carry hardware metadata such as:

thread / bolt size
channel nut type
washer requirements
hardware preset
BOM line items

Fastener geometry should be handled later through FreeCAD Fasteners or compatible tooling.

Development install

During development, symlink or copy the workbench into your FreeCAD Mod directory.

Example Linux Snap-style development layout:

~/src/UnistrutWB/Mod/UnistrutWB
~/snap/freecad/common/Mod/UnistrutWB -> ~/src/UnistrutWB/Mod/UnistrutWB

Restart FreeCAD after code changes unless using manual module reloads.

Quick smoke test
Open FreeCAD.
Switch to the UnistrutWB workbench.
Use New Channel to create a P4100 channel.
Use Add Fitting.
Confirm the dialog shows fitting categories and variants.
Create a P1065 splice plate or DEV_ANGLE_90_2LEG angle bracket.
Select the generated fitting and confirm catalog metadata appears in the property panel.
Use FreeCAD Assembly for final placement or constraint experiments.
Current roadmap

Near-term priorities:

Keep Add Fitting focused on catalog object authoring.
Improve fitting schema and metadata.
Define Assembly-facing mate-frame/reference contracts.
Improve BOM/export fidelity.
Normalize more catalog records.
Add more fitting families and variants.
Document placement as convenience-level, not solver-level.

Non-goals for MVP:

Full Unistrut assembly solving inside UnistrutWB
Multi-channel splice-joint inference
Bolt stack solving
Fastener geometry generation from scratch
One-click final mechanical placement
Project status

This project is under active development on the dev branch.

The current MVP direction is:

catalog normalization -> CAD object generation -> metadata/BOM -> Assembly/Fasteners integration
