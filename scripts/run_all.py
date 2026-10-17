#!/usr/bin/env python3
"""Run the full pack and rewrite every published artefact.

    python3 scripts/run_all.py

Nothing beyond the standard library is needed for the analysis. Chart rendering
needs Pillow; every other artefact is written with or without it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pack import pipeline  # noqa: E402


def main() -> int:
    summary = pipeline.run()
    for name, value in summary.items():
        print(f"{name:22s} {value}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
