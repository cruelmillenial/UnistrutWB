"""
Orchestrator: Extract -> Transform -> Load.

Usage:
  python etl/run_etl.py --pdf ../unistrut-general-catalog.pdf --out ../Mod/UnistrutWB/data --log ../logs
"""
from __future__ import annotations
import argparse, json, datetime, hashlib
from pathlib import Path
from etl.extract_pdf import extract
from etl.transform import load_staging, transform
from etl.load import load as load_out

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--staging", default="staging")
    args = ap.parse_args()

    log_dir = Path(args.log)
    log_dir.mkdir(parents=True, exist_ok=True)

    ex = extract(args.pdf, args.staging)

    meta = {
        "vendor": "Unistrut",
        "catalog": {
            "source_file": Path(args.pdf).name,
            "sha256": sha256_file(args.pdf),
            "ingested_at": datetime.datetime.now().isoformat(timespec="seconds"),
        },
        "units": {"internal": "SI", "display_default": "imperial"},
        "schema_version": "0.1.0",
    }

    staging = load_staging(args.staging)
    ds = transform(staging, meta)
    shas = load_out(ds, args.out)

    log = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "extract": ex,
        "outputs": shas,
        "coverage": {
            "profiles": len(ds["profiles"]),
            "fittings": len(ds["fittings"]),
            "hardware": len(ds["hardware"]),
            "finishes": len(ds["finishes"]),
            "load_tables": len(ds["load_tables"]),
        },
        "known_gaps": [
            "No automated PDF table extraction yet (seed staging only).",
            "Pierced variant patterns not populated.",
            "No real fittings catalog parse yet (placeholder only).",
            "No beam/column load tables extracted yet.",
        ],
    }
    log_path = log_dir / f"etl_run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    log_path.write_text("```json\n" + json.dumps(log, indent=2) + "\n```\n", encoding="utf-8")
    print("OK")
    print(json.dumps(log["outputs"], indent=2))

if __name__ == "__main__":
    main()
