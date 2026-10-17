#!/usr/bin/env python3
"""Rewrite a committed month fixture from the current renderers.

    python3 scripts/make_fixture.py --month 2025-12

The fixture is the answer key and the two markdown documents for a month other
than the published one, so `make test` proves the renderers on data they were
not written against. Run this only when a renderer change is deliberate; the
diff is then the review of that change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pack import generator, key, render  # noqa: E402
from pack.analysis import analyse_month  # noqa: E402
from pack.model import MONTHS, Ledger  # noqa: E402

FIXTURE_MONTH = "2025-12"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--month",
        default=FIXTURE_MONTH,
        help=f"month to capture (default: {FIXTURE_MONTH})",
    )
    args = parser.parse_args(argv)

    if args.month not in MONTHS:
        raise KeyError(f"{args.month} is not in this ledger")

    ledger = Ledger.from_dict(generator.build_ledger())
    analysis = analyse_month(ledger, args.month)
    answer_key = key.build_answer_key(ledger, args.month)

    directory = ROOT / "tests" / "fixtures" / args.month
    directory.mkdir(parents=True, exist_ok=True)
    key.write_json(answer_key, directory / "answer_key.json")
    (directory / "answer_key.md").write_text(
        render.answer_key_md(answer_key), encoding="utf-8"
    )
    (directory / "MONTHLY_PACK.md").write_text(
        render.monthly_pack(analysis, answer_key), encoding="utf-8"
    )

    for name in ("answer_key.json", "answer_key.md", "MONTHLY_PACK.md"):
        print(f"wrote  {directory / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
