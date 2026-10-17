"""CSV tables: the artefact a reader filters in a spreadsheet.

Every table is written in the wire format (``money.plain``): no separators, so a
spreadsheet parses the column as a number rather than text.
"""

import csv
from pathlib import Path

from . import money, variance
from .model import Ledger


def write_tables(
    ledger: Ledger, analysis: variance.MonthAnalysis, directory: Path
) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    written = []

    bridge_path = directory / "bridge.csv"
    with bridge_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["component", "kes"])
        for name, value in analysis.bridge.components.items():
            writer.writerow([name, money.plain(value)])
        writer.writerow(["total", money.plain(analysis.bridge.total_variance)])
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
                    money.plain(row.gross_profit_impact),
                    row.owner,
                    row.action,
                ]
            )
    written.append(exceptions_path)

    lines_path = directory / "line_variance.csv"
    with lines_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "branch", "sku", "product", "category", "owner",
                "units_budget", "units_actual", "gp_budget", "gp_actual",
                "variance", "price", "cost_rate", "volume_revenue", "volume_cost",
            ]
        )
        for row in variance.line_variances(ledger, analysis.month):
            writer.writerow(
                [
                    row.branch, row.sku, row.product, row.category, row.owner,
                    row.units_budget, row.units_actual, money.plain(row.gp_budget),
                    money.plain(row.gp_actual), money.plain(row.variance),
                    money.plain(row.price), money.plain(row.cost_rate),
                    money.plain(row.volume_revenue), money.plain(row.volume_cost),
                ]
            )
    written.append(lines_path)

    trend_path = directory / "branch_trend.csv"
    with trend_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["branch", "window", "units_budget", "units_actual",
             "volume_effect", "variance_pct", "adverse_months", "off_track"]
        )
        for row in variance.branch_trends(ledger, analysis.month):
            writer.writerow(
                [
                    row.branch, " ".join(row.window), row.units_budget,
                    row.units_actual, money.plain(row.volume_effect),
                    money.pct(row.variance_pct), row.adverse_months, row.is_off_track,
                ]
            )
    written.append(trend_path)

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
                        money.plain(row.budget_gross_profit),
                        money.plain(row.actual_gross_profit),
                        money.plain(row.variance),
                        money.pct(row.variance_pct),
                    ]
                )
        written.append(path)

    return written
