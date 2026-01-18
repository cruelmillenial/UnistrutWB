"""
Extract layer (Raw -> Staging).

This is a *starter* extractor:
- It does NOT try to perfectly parse the PDF.
- It creates staging CSV templates you can fill/patch, while still capturing provenance.

Later upgrades:
- Camelot / Tabula table extraction
- Custom regex over text spans for "BOLT TORQUE" / finish tables
- Screenshot-driven manual QA for tables

Outputs (staging/):
- profiles_seed.csv
- finishes_seed.csv
- torque_seed.csv
- fittings_seed.csv
"""
from __future__ import annotations
import os, csv, datetime
from pathlib import Path

def write_if_missing(path: Path, header: list[str], rows: list[list[str]]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def extract(pdf_path: str, staging_dir: str) -> dict:
    staging = Path(staging_dir)
    ts = datetime.datetime.now().isoformat(timespec="seconds")

    write_if_missing(
        staging / "profiles_seed.csv",
        ["id","family","gauge","width_in","height_in","thickness_in","finishes_csv","std_lengths_ft_csv","source_pages_csv","notes"],
        [
            ["P1000","1-5/8 x 1-5/8","12","1.625","1.625","0.105","EG,HG,GR,PL,PG,DF,ZD","10,20","","Seed row; fill from catalog table."],
            ["P4100","1-5/8 x 13/16","14","1.625","0.8125","0.075","EG,HG,GR,PL,PG,DF,ZD","10,20","","Seed row; fill from catalog table."],
        ],
    )

    write_if_missing(
        staging / "finishes_seed.csv",
        ["code","name","standards_csv","source_pages_csv","notes"],
        [
            ["EG","Electro-galvanized","ASTM B633 Type III SC1","",""],
            ["HG","Hot-dipped galvanized","ASTM A123;ASTM A153","",""],
            ["GR","Green Powder Coat","Commercial powder coating standards","",""],
            ["PG","Pre-galvanized","ASTM A653 G90","",""],
            ["PL","Plain","","",""],
            ["DF","Unistrut Defender","ASTM A1046;ASTM A1059","",""],
            ["ZD","Perma-Gold","ASTM B633 Type II SC3","",""],
        ],
    )

    write_if_missing(
        staging / "torque_seed.csv",
        ["thread","rec_ft_lb","rec_N_m","max_ft_lb","max_N_m","source_pages_csv","notes"],
        [
            ["1/4-20","6","8","7","9","","From catalog torque table; verify."],
            ["5/16-18","11","15","15","20","","From catalog torque table; verify."],
            ["3/8-16","19","26","25","34","","From catalog torque table; verify."],
            ["1/2-13","50","68","70","95","","From catalog torque table; verify."],
            ["5/8-11","100","136","125","170","","From catalog torque table; verify."],
            ["3/4-10","125","170","135","183","","From catalog torque table; verify."],
        ],
    )

    write_if_missing(
        staging / "fittings_seed.csv",
        ["id","name","category","thickness_in","hole_diam_in","hole_pattern","source_pages_csv","notes"],
        [
            ["GEN_ANGLE_90","Generic 90° Angle Plate (placeholder)","angle","0.25","0.5625","1-7/8 pitch","","Placeholder record for acceptance tests."],
        ],
    )

    return {
        "timestamp": ts,
        "pdf": os.path.abspath(pdf_path),
        "staging_dir": os.path.abspath(staging_dir),
        "status": "ok",
        "notes": [
            "Seed staging CSVs created if missing.",
            "Populate/replace staging rows as you extract real catalog tables.",
        ],
    }
