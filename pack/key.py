"""The answer key: every published number, in one schema.

This is the source of truth the README quotes and the validation report checks,
so the schema lives on its own rather than inside the CLI module.
"""

import json
from pathlib import Path

from . import bridge as bridge_mod
from . import lines, money, render, trends
from .analysis import analyse_month
from .model import Ledger


def build_answer_key(ledger: Ledger, month: str) -> dict:
    analysis = analyse_month(ledger, month)
    bridge = analysis.bridge

    return {
        "month": month,
        "fingerprint": ledger.fingerprint,
        "seed": ledger.seed,
        "headline": {
            "revenue_budget": money.plain(analysis.budget_revenue),
            "revenue_actual": money.plain(analysis.actual_revenue),
            "revenue_variance": money.plain(
                analysis.actual_revenue - analysis.budget_revenue
            ),
            "revenue_variance_pct": money.pct(
                (analysis.actual_revenue / analysis.budget_revenue - 1) * 100
            ),
            "gross_profit_budget": money.plain(analysis.budget_gross_profit),
            "gross_profit_actual": money.plain(analysis.actual_gross_profit),
            "gross_profit_variance": money.plain(analysis.gross_profit_variance),
            "gross_profit_variance_pct": money.pct(analysis.variance_pct),
            "largest_driver": analysis.largest_driver,
        },
        "bridge": {
            "budget_gross_profit": money.plain(bridge.budget_gp),
            "flexed_gross_profit": money.plain(bridge.flexed_gp),
            "volume": money.plain(bridge.volume),
            "mix": money.plain(bridge.mix),
            "price": money.plain(bridge.price),
            "cost": money.plain(bridge.cost),
            "total": money.plain(bridge.total_variance),
        },
        "owners": {
            owner: money.plain(value)
            for owner, value in bridge_mod.owner_totals(bridge).items()
        },
        "by_branch": [
            {
                "branch": row.label,
                "budget_gross_profit": money.plain(row.budget_gross_profit),
                "actual_gross_profit": money.plain(row.actual_gross_profit),
                "variance": money.plain(row.variance),
                "variance_pct": money.pct(row.variance_pct),
            }
            for row in analysis.by_branch
        ],
        "by_category": [
            {
                "category": row.label,
                "budget_gross_profit": money.plain(row.budget_gross_profit),
                "actual_gross_profit": money.plain(row.actual_gross_profit),
                "variance": money.plain(row.variance),
                "variance_pct": money.pct(row.variance_pct),
            }
            for row in analysis.by_category
        ],
        "exceptions": [
            {
                "scope": row.scope,
                "label": row.label,
                "driver": row.driver,
                "gross_profit_impact": money.plain(row.gross_profit_impact),
                "owner": row.owner,
                "action": render.exception_action(row),
                "finding": render.exception_finding(row),
            }
            for row in analysis.exceptions
        ],
        "lines": [
            {
                "branch": row.branch,
                "sku": row.sku,
                "product": row.product,
                "category": row.category,
                "owner": row.owner,
                "units_budget": row.units_budget,
                "units_actual": row.units_actual,
                "gp_budget": money.plain(row.gp_budget),
                "gp_actual": money.plain(row.gp_actual),
                "variance": money.plain(row.variance),
                "price": money.plain(row.price),
                "cost_rate": money.plain(row.cost_rate),
                "volume_revenue": money.plain(row.volume_revenue),
                "volume_cost": money.plain(row.volume_cost),
            }
            for row in lines.line_variances(ledger, month)
        ],
        "branch_trends": [
            {
                "branch": row.branch,
                "window": list(row.window),
                "units_budget": row.units_budget,
                "units_actual": row.units_actual,
                "volume_effect": money.plain(row.volume_effect),
                "variance_pct": money.pct(row.variance_pct),
                "adverse_months": row.adverse_months,
                "off_track": row.is_off_track,
            }
            for row in trends.branch_trends(ledger, month)
        ],
        "materiality": money.plain(analysis.materiality),
        "trend": [
            {
                "month": row["month"],
                "budget_gross_profit": money.plain(row["budget_gross_profit"]),
                "actual_gross_profit": money.plain(row["actual_gross_profit"]),
                "variance": money.plain(row["variance"]),
            }
            for row in trends.trend(ledger)
        ],
    }


def write_json(key: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    return path
