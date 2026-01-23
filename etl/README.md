# Unistrut_ETL (DATALAB)

This folder contains the **reproducible ETL pipeline** that turns `unistrut-general-catalog.pdf`
into git-friendly, versioned JSON artifacts consumed by the FreeCAD workbench.

## Philosophy
- **JSON-first** for diffs / review.
- **Dual-unit storage** (original + SI).
- **Provenance on every record** (page anchors, table ids).
- **Staging-first extraction**: start manual/semi-automated; replace extractors later.

## Run
```bash
python etl/run_etl.py \
  --pdf ../unistrut-general-catalog.pdf \
  --out ../Mod/UnistrutWB/data \
  --log ../logs
```

> Note: `extract_pdf.py` is intentionally conservative: it produces *staging CSVs*
and asks you to confirm coverage. Replace with `camelot`/`tabula`/vendor APIs when ready.
