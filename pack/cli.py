"""Command line: one month, written to a scratch directory.

The documented command is a scratch run, not a release. It writes under
``scratch/<month>/`` (git-ignored), so a reader who follows the README cannot
overwrite the committed pack; ``make run`` is the only path that regenerates the
release artefacts in ``outputs/``.
"""

import argparse
from pathlib import Path

from . import pipeline
from .model import MONTHS

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = "scratch"


def default_root(month: str) -> Path:
    """Where a scratch run for ``month`` belongs, unless told otherwise."""
    return ROOT / SCRATCH / month


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the monthly management pack for one month into a scratch "
            "directory. Use `make run` to regenerate the published artefacts."
        )
    )
    parser.add_argument(
        "--month",
        default=pipeline.DEFAULT_MONTH,
        help="month to report on, as YYYY-MM (default: the last month in the ledger)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="directory to write into (default: scratch/<month>)",
    )
    args = parser.parse_args(argv)

    if args.month not in MONTHS:
        raise KeyError(f"{args.month} is not in this ledger")

    out = Path(args.out) if args.out else default_root(args.month)
    summary = pipeline.run(month=args.month, root=out)

    print(f"month            {summary['month']}")
    print(f"ledger           {summary['fingerprint']}")
    print(f"gross profit var {summary['gross_profit_variance']}")
    print(f"exceptions       {summary['exceptions']}")
    print(
        f"checks           {summary['checks']} "
        f"({'all pass' if summary['all_passed'] else 'FAILED'})"
    )
    print(f"written to       {out}")
    return 0 if summary["all_passed"] else 1
