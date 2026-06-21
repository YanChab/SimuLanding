"""Regenerate the aircraft golden file used by test_aircraft_regression.

Usage:
    /Users/neoyan/SimuLanding/.venv/bin/python scripts/regen_golden_aircraft_test.py
"""

from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(repo_root))

    from tests.test_aircraft_regression import GOLDEN_JSON, regenerate_golden

    regenerate_golden()
    print(f"[ok] golden regenerated: {GOLDEN_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
