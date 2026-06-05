#!/usr/bin/env python3
"""
Run all no-FreeCAD schema smoke checks.

Run from repo root:

    python3 scripts/smoke_all_schema.py

No FreeCAD dependency.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("fittings", REPO_ROOT / "scripts" / "smoke_fittings_schema.py"),
    ("profiles", REPO_ROOT / "scripts" / "smoke_profiles_schema.py"),
]


def run_check(name: str, script: Path) -> int:
    print(f"==> schema smoke: {name}")

    if not script.exists():
        print(f"ERROR: missing smoke script: {script}", file=sys.stderr)
        return 2

    result = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT)

    if result.returncode == 0:
        print(f"==> schema smoke: {name} passed")
    else:
        print(
            f"==> schema smoke: {name} FAILED with exit code {result.returncode}",
            file=sys.stderr,
        )

    print()
    return result.returncode


def main() -> int:
    failures: list[tuple[str, int]] = []

    for name, script in CHECKS:
        code = run_check(name, script)
        if code != 0:
            failures.append((name, code))

    if failures:
        print("combined schema smoke test FAILED", file=sys.stderr)
        for name, code in failures:
            print(f"- {name}: exit code {code}", file=sys.stderr)
        return 1

    print("combined schema smoke test passed")
    print(f"validated {len(CHECKS)} schema smoke check(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
