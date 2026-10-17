"""The published artefacts: answer key, monthly pack, and tables.

The answer key is the single source of truth for every number quoted in the
README. The pack is generated from the same analysis, never written by hand.
"""

import csv
import json
from decimal import Decimal
from pathlib import Path

from . import variance
from .model import Ledger

CENT = Decimal("0.01")


def _money(value) -> str:
    return str(Decimal(value).quantize(CENT))


def _pct(value) -> str:
    return str(Decimal(value).quantize(CENT))


def _thousands(value) -> str:
    return f"{Decimal(value):,.2f}"


def build_answer_key(ledger: Ledger, month: str) -> dict:
    analysis = variance.analyse_month(ledger, month)
    bridge = analysis.bridge

    return {
        "month": month,
        "fingerprint": ledger.fingerprint,
        "seed": ledger.seed,
        "headline": {
            "revenue_budget": _money(analysis.budget_revenue),
            "revenue_actual": _money(analysis.actual_revenue),
            "revenue_variance": _money(analysis.actual_revenue - analysis.budget_revenue),
            "revenue_variance_pct": _pct(
                (analysis.actual_revenue / analysis.budget_revenue - 1) * 100
            ),
            "gross_profit_budget": _money(analysis.budget_gross_profit),
            "gross_profit_actual": _money(analysis.actual_gross_profit),
            "gross_profit_variance": _money(analysis.gross_profit_variance),
            "gross_profit_variance_pct": _pct(analysis.variance_pct),
            "largest_driver": analysis.largest_driver,
        },
        "bridge": {
            "budget_gross_profit": _money(bridge.budget_gp),
            "flexed_gross_profit": _money(bridge.flexed_gp),
            "volume": _money(bridge.volume),
            "mix": _money(bridge.mix),
            "price": _money(bridge.price),
            "cost": _money(bridge.cost),
            "total": _money(bridge.total_variance),
        },
        "owners": {
            owner: _money(value)
            for owner, value in variance.owner_totals(bridge).items()
        },
        "by_branch": [
            {
                "branch": row.label,
                "budget_gross_profit": _money(row.budget_gross_profit),
                "actual_gross_profit": _money(row.actual_gross_profit),
                "variance": _money(row.variance),
                "variance_pct": _pct(row.variance_pct),
            }
            for row in analysis.by_branch
        ],
        "by_category": [
            {
                "category": row.label,
                "budget_gross_profit": _money(row.budget_gross_profit),
                "actual_gross_profit": _money(row.actual_gross_profit),
                "variance": _money(row.variance),
                "variance_pct": _pct(row.variance_pct),
            }
            for row in analysis.by_category
        ],
        "exceptions": [
            {
                "scope": row.scope,
                "label": row.label,
                "driver": row.driver,
                "gross_profit_impact": _money(row.gross_profit_impact),
                "owner": row.owner,
                "action": row.action,
                "finding": row.finding,
            }
            for row in analysis.exceptions
        ],
        "materiality": _money(analysis.materiality),
        "trend": [
            {
                "month": row["month"],
                "budget_gross_profit": _money(row["budget_gross_profit"]),
                "actual_gross_profit": _money(row["actual_gross_profit"]),
                "variance": _money(row["variance"]),
            }
            for row in variance.trend(ledger)
        ],
    }


def render_pack(analysis: variance.MonthAnalysis, key: dict) -> str:
    headline = key["headline"]
    bridge = key["bridge"]
    revenue_gap = Decimal(headline["revenue_variance_pct"])
    profit_gap = Decimal(headline["gross_profit_variance_pct"])
    variance_total = Decimal(headline["gross_profit_variance"])

    lines = [
        f"# Monthly management pack — {analysis.month}",
        "",
        (
            "> **Synthetic data.** Every figure below is generated from a seeded, "
            f"documented mechanism (ledger fingerprint `{key['fingerprint']}`). "
            "No client figures appear in this pack."
        ),
        "",
        "## Headline",
        "",
        "| | Budget | Actual | Variance | Variance % |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Revenue | {_thousands(headline['revenue_budget'])} | "
            f"{_thousands(headline['revenue_actual'])} | "
            f"{_thousands(headline['revenue_variance'])} | "
            f"{revenue_gap}% |"
        ),
        (
            f"| Gross profit | {_thousands(headline['gross_profit_budget'])} | "
            f"{_thousands(headline['gross_profit_actual'])} | "
            f"{_thousands(headline['gross_profit_variance'])} | "
            f"{profit_gap}% |"
        ),
        "",
        (
            f"Revenue came in {abs(revenue_gap)}% off budget; gross profit came in "
            f"{abs(profit_gap)}% off it, a shortfall of "
            f"KES {_thousands(abs(variance_total))}. The gap between those two "
            "percentages is the whole story of the month: the business sold roughly "
            "the volume it planned and kept far less of the money."
        ),
        "",
        "## The bridge",
        "",
        "| Driver | KES | Share of budget gross profit |",
        "|---|---:|---:|",
    ]

    budget_gp = Decimal(bridge["budget_gross_profit"])
    for name, label in (
        ("volume", "Volume — total units at budget margin per unit"),
        ("mix", "Mix — selling a different blend at budget margins"),
        ("price", "Price — actual units at the change in selling price"),
        ("cost", "Cost — actual units at the change in unit cost"),
    ):
        value = Decimal(bridge[name])
        share = (value / budget_gp * 100).quantize(CENT) if budget_gp else Decimal("0")
        lines.append(f"| {label} | {_thousands(value)} | {share}% |")
    lines.append(f"| **Total variance** | **{_thousands(Decimal(bridge['total']))}** | |")
    lines.append("")
    lines.append(
        "Reconciliation: "
        f"{_thousands(bridge['volume'])} + {_thousands(bridge['mix'])} + "
        f"{_thousands(bridge['price'])} + {_thousands(bridge['cost'])} = "
        f"{_thousands(bridge['total'])}, which equals actual gross profit less "
        "budget gross profit to the cent. The flexed budget — actual volume at "
        f"budget price and cost — is {_thousands(bridge['flexed_gross_profit'])}: "
        "volume plus mix accounts for the difference between budget and flex, "
        "price plus cost for the difference between flex and actual."
    )
    lines.append("")

    lines += [
        "## Exceptions",
        "",
        f"Lines at or beyond the materiality threshold of "
        f"KES {_thousands(key['materiality'])}.",
        "",
        "| Line | Finding | Driver | Impact (KES) | Owner | Action |",
        "|---|---|---|---:|---|---|",
    ]
    for row in key["exceptions"]:
        lines.append(
            f"| {row['label']} | {row['finding']} | {row['driver']} | "
            f"{_thousands(row['gross_profit_impact'])} | {row['owner']} | "
            f"{row['action']} |"
        )
    lines.append("")

    lines += [
        "## Where it sits",
        "",
        "### By branch",
        "",
        "| Branch | Budget GP | Actual GP | Variance | % |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in key["by_branch"]:
        lines.append(
            f"| {row['branch']} | {_thousands(row['budget_gross_profit'])} | "
            f"{_thousands(row['actual_gross_profit'])} | "
            f"{_thousands(row['variance'])} | {row['variance_pct']}% |"
        )
    lines += [
        "",
        "### By category",
        "",
        "| Category | Budget GP | Actual GP | Variance | % |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in key["by_category"]:
        lines.append(
            f"| {row['category']} | {_thousands(row['budget_gross_profit'])} | "
            f"{_thousands(row['actual_gross_profit'])} | "
            f"{_thousands(row['variance'])} | {row['variance_pct']}% |"
        )
    lines.append("")

    lines += ["## What I would do first", ""]
    for index, row in enumerate(key["exceptions"][:3], start=1):
        lines.append(
            f"{index}. **{row['owner']}** — {row['action']}. "
            f"Worth KES {_thousands(abs(Decimal(row['gross_profit_impact'])))} "
            f"of gross profit, review date the last working day of next month."
        )
    lines += [
        "",
        "## Method and limits",
        "",
        "- Budget is set once per calendar year; the actuals drift from it through "
        "four documented mechanisms plus seeded noise.",
        "- Mix is the part of the volume movement not explained by total units, so "
        "the four components reconcile exactly rather than approximately.",
        "- Single currency (KES), no tax, no foreign exchange, no write-offs, no "
        "allocation of overhead. This is a gross-profit pack, not a P&L.",
        "- Regenerate with `make run`; the ledger fingerprint proves the run.",
        "",
    ]
    return "\n".join(lines)


def render_answer_key_md(key: dict) -> str:
    headline = key["headline"]
    bridge = key["bridge"]
    lines = [
        f"# Answer key — {key['month']}",
        "",
        f"Ledger fingerprint `{key['fingerprint']}` (seed {key['seed']}). "
        "Synthetic data, disclosed.",
        "",
        "## Headline",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Revenue — budget | {_thousands(headline['revenue_budget'])} |",
        f"| Revenue — actual | {_thousands(headline['revenue_actual'])} |",
        f"| Revenue — variance | {headline['revenue_variance_pct']}% |",
        f"| Gross profit — budget | {_thousands(headline['gross_profit_budget'])} |",
        f"| Gross profit — actual | {_thousands(headline['gross_profit_actual'])} |",
        f"| Gross profit — variance | {_thousands(headline['gross_profit_variance'])} "
        f"({headline['gross_profit_variance_pct']}%) |",
        f"| Largest driver | {headline['largest_driver']} |",
        "",
        "## Bridge",
        "",
        "| Component | KES |",
        "|---|---:|",
    ]
    for name in ("budget_gross_profit", "volume", "mix", "price", "cost", "actual_gross_profit"):
        if name == "actual_gross_profit":
            value = Decimal(bridge["budget_gross_profit"]) + Decimal(bridge["total"])
            lines.append(f"| **Actual gross profit** | **{_thousands(value)}** |")
            continue
        lines.append(f"| {name.replace('_', ' ').capitalize()} | {_thousands(bridge[name])} |")
    lines.append(f"| **Total variance** | **{_thousands(Decimal(bridge['total']))}** |")
    lines += ["", "## Owners", "", "| Owner | Variance (KES) |", "|---|---:|"]
    for owner, value in key["owners"].items():
        lines.append(f"| {owner} | {_thousands(value)} |")
    lines += ["", "## Exceptions", ""]
    for row in key["exceptions"]:
        lines.append(
            f"- **{row['label']}** ({row['driver']}, "
            f"KES {_thousands(row['gross_profit_impact'])}) — {row['finding']} "
            f"*Owner: {row['owner']}.*"
        )
    lines.append("")
    return "\n".join(lines)


def write_tables(analysis: variance.MonthAnalysis, directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []

    bridge_path = directory / "bridge.csv"
    with bridge_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["component", "kes"])
        for name, value in analysis.bridge.components.items():
            writer.writerow([name, _money(value)])
        writer.writerow(["total", _money(analysis.bridge.total_variance)])
    written.append(bridge_path)

    exceptions_path = directory / "exceptions.csv"
    with exceptions_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["scope", "label", "driver", "impact", "owner", "action"])
        for row in analysis.exceptions:
            writer.writerow(
                [
                    row.scope,
                    row.label,
                    row.driver,
                    _money(row.gross_profit_impact),
                    row.owner,
                    row.action,
                ]
            )
    written.append(exceptions_path)

    for filename, rows, label in (
        ("branch_variance.csv", analysis.by_branch, "branch"),
        ("category_variance.csv", analysis.by_category, "category"),
    ):
        path = directory / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([label, "budget_gp", "actual_gp", "variance", "variance_pct"])
            for row in rows:
                writer.writerow(
                    [
                        row.label,
                        _money(row.budget_gross_profit),
                        _money(row.actual_gross_profit),
                        _money(row.variance),
                        _pct(row.variance_pct),
                    ]
                )
        written.append(path)

    return written


def write_json(key: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    """python -m pack.report --month 2026-06"""
    import argparse

    from . import pipeline

    parser = argparse.ArgumentParser(
        description="Build the monthly management pack for one month."
    )
    parser.add_argument(
        "--month",
        default=pipeline.DEFAULT_MONTH,
        help="month to report on, as YYYY-MM (default: the last month in the ledger)",
    )
    args = parser.parse_args(argv)

    summary = pipeline.run(month=args.month)
    print(f"month            {summary['month']}")
    print(f"ledger           {summary['fingerprint']}")
    print(f"gross profit var {summary['gross_profit_variance']}")
    print(f"exceptions       {summary['exceptions']}")
    print(f"checks           {summary['checks']} ({'all pass' if summary['all_passed'] else 'FAILED'})")
    print("written to outputs/")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
