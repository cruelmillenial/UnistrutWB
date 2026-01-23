# UnistrutWB (DATALAB)

A **catalog-driven Unistrut ETL + FreeCAD Workbench scaffold**.

This repo is organized per the Copilot ETL/WB roadmap: JSON-first datastore consumed by a FreeCAD workbench with commands for **New Channel**, **Add Fitting**, **Snap/Mate**, and **BOM Export**. fileciteturn1file1

## What you get (v0.1)
- `Mod/UnistrutWB/data/unistrut.json` — **seed datastore** (2 profiles + 1 fitting + torque spec + finishes)
- `Mod/UnistrutWB/data/mapping_hole_series.json` — hole series + derating rules
- `Mod/UnistrutWB/data/notes_derating.json` — global notes/provenance anchors
- `etl/` — Extract → Transform → Load pipeline (staging CSVs + pandas canonicalization)
- `Mod/UnistrutWB/` — FreeCAD workbench scaffold (toolbar + 4 commands)

## Provenance strategy
Every record has a `provenance` field (pages, table ids, notes). The ETL runner also records a PDF SHA256 checksum in `meta.catalog.sha256` so future catalogs can be diffed cleanly. fileciteturn1file3

## Install into FreeCAD
1. Copy `Mod/UnistrutWB` into your FreeCAD user Mod directory:
   - Linux: `~/.local/share/FreeCAD/Mod/UnistrutWB` *(varies by distro/package)*
2. Ensure the JSON files live at:
   `.../Mod/UnistrutWB/data/unistrut.json` etc.
3. Restart FreeCAD → enable the **UnistrutWB** workbench.

### Quick test
- Workbench → **New Channel** → select `P1000` → OK
- Workbench → **Add Fitting** → select `GEN_ANGLE_90` → OK
- Select the two objects → **Snap/Mate**
- Workbench → **BOM Export** → save CSV

## Run the ETL
```bash
cd UnistrutWB
python etl/run_etl.py \
  --pdf unistrut-general-catalog.pdf \
  --out Mod/UnistrutWB/data \
  --log logs
```

This creates `logs/etl_run_YYYYMMDD_HHMMSS.md` with coverage and gaps.

## Next upgrades (planned)
- Real table extraction (Camelot/Tabula or targeted regex per section).
- Populate:
  - section properties (I, S, r), weight
  - beam/column load tables and support-condition multipliers
  - real fittings library (geometry + mate frames)
- Replace placeholder fitting solids with parametric bodies.
- Real LCS/datum mating (Assembly workbench compatible).

