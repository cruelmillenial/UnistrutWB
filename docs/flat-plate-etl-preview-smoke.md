# Flat-plate ETL reference preview — experimental smoke test

This **development branch only** demonstrates the complete path from the upstream
`strut-catalog-etl` reference snapshot to real FreeCAD solids with through-holes.

**No manufacturer-exact claim is made.** The six entries in
`Mod/UnistrutWB/data/fittings_preview.json` are copied from the upstream
`generated/preview/flat_plate_fittings.json` on ETL PR #4. They deliberately use
`REF_` IDs, `preview_only` status, and *Reference Plates (Provisional)* menu
grouping. Their longitudinal hole positions and diameter come from the catalog;
transverse centerline and sharp corners are declared approximations. Material
thickness variants represent **conditional steel-grade rules**, not verification
of any particular purchased piece.

## GUI check on the user workstation

1. Check out `feature/flat-plate-etl-preview` in UnistrutWB and activate this
   checkout as the FreeCAD Workbench (restart FreeCAD if already loaded).
2. Open the FreeCAD Python console and run:

   `import runpy; runpy.run_path("/absolute/path/to/UnistrutWB/scripts/smoke_flat_plate_preview.py", run_name="__main__")`

3. Expected: three physically holed plates P1065, P1066, P1067 appear next to
   each other in an axonometric view and three `PASS` messages print. The smoke
   script asserts each shape is a valid single solid, checks dimensions and
   checks the removed cylinder volumes.
4. In the Workbench, use **Add Fitting → Reference Plates (Provisional)**.
   Select a `REF_P1065_SS33`-family entry and insert it without selecting a
   channel first. The geometry should contain two real holes. The resulting
   object label includes `[NON-RELEASE REFERENCE]`, and its properties preserve
   the source hash and inferred geometry caveats.

## Limitations

- The legacy `P1065` placeholder is untouched and still produces an unholed
  block; the `REF_...` records are distinct and cannot overwrite it.
- Hole-diameter customization is deliberately *not implemented* for reference
  entries: each preview offers only the catalog reference diameter (9/16 in).
  Variable clearance sizing belongs in the later custom-variant feature.
- The FreeCAD geometry check requires FreeCAD's `Part` kernel and must be run on
  a machine with FreeCAD; ETL CI cannot establish the solid geometry by itself.
- No release data are substituted or auto-synchronized. These preview bytes
  must be manually refreshed from the ETL repo until the separate cross-repo
  delivery CI is implemented.
- P1068 is an angle family and is not part of this demonstration.
