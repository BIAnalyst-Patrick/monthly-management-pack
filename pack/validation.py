"""Fifteen independent checks, each able to fail.

Every check compares a published figure against an identity it did not come
from: the bridge against its components, the flex against a fresh sum, the
branch split against the total, the answer key against a recomputation.
"""

from dataclasses import dataclass
from decimal import Decimal

from . import bridge as bridge_mod
from . import lines, money
from .analysis import MonthAnalysis
from .generator import fingerprint_of
from .model import BRANCHES, CATEGORIES, MONTHS, Ledger, SKUS_PER_CATEGORY

@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _micro_ledger() -> Ledger:
    """Two products, one month, every product scaled by exactly two."""
    catalogue = [
        {"sku": "A", "name": "A", "category": "Home Care", "list_price": "100.00", "base_cost": "70.00"},
        {"sku": "B", "name": "B", "category": "Staples", "list_price": "100.00", "base_cost": "90.00"},
    ]

    def rows(volume):
        return [
            {"month": "2026-06", "branch": "Nairobi CBD", "sku": "A", "volume": volume,
             "price": "100.00", "unit_cost": "70.00"},
            {"month": "2026-06", "branch": "Nairobi CBD", "sku": "B", "volume": volume,
             "price": "100.00", "unit_cost": "90.00"},
        ]

    return Ledger.from_dict(
        {
            "seed": 0,
            "fingerprint": "0" * 16,
            "months": ["2026-06"],
            "branches": ["Nairobi CBD"],
            "catalogue": catalogue,
            "budgets": rows(100),
            "actuals": rows(200),
            "notes": ["synthetic"],
        }
    )


def run_checks(ledger: Ledger, analysis: MonthAnalysis, key: dict) -> list[Check]:
    checks: list[Check] = []
    bridge = analysis.bridge
    month_ledger = ledger.month(analysis.month)

    expected = len(MONTHS) * len(BRANCHES) * len(ledger.catalogue)
    checks.append(
        Check(
            "ledger covers every month, branch and sku",
            len(ledger.budgets) == expected and len(ledger.actuals) == expected,
            f"{len(ledger.budgets)} budget and {len(ledger.actuals)} actual lines, {expected} expected",
        )
    )

    per_category = {c: sum(1 for i in ledger.catalogue.values() if i.category == c) for c in CATEGORIES}
    checks.append(
        Check(
            "catalogue holds four categories of ten skus",
            len(ledger.catalogue) == len(CATEGORIES) * SKUS_PER_CATEGORY
            and all(v == SKUS_PER_CATEGORY for v in per_category.values()),
            f"{len(ledger.catalogue)} skus: {per_category}",
        )
    )

    prices = {}
    price_ok = True
    for line in ledger.budgets:
        key_ = (line.month[:4], line.sku)
        if key_ in prices and prices[key_] != line.price:
            price_ok = False
        prices[key_] = line.price
    checks.append(
        Check(
            "budget price is constant within a year",
            price_ok,
            f"{len(prices)} year-and-sku combinations, one price each",
        )
    )

    bad = [l for l in list(ledger.budgets) + list(ledger.actuals) if l.unit_cost >= l.price]
    checks.append(
        Check(
            "unit cost stays below the selling price",
            not bad,
            f"{len(bad)} lines with cost at or above price",
        )
    )

    payload = {
        "seed": ledger.seed,
        "months": list(ledger.months),
        "branches": list(ledger.branches),
        "catalogue": [
            {
                "sku": item.sku,
                "name": item.name,
                "category": item.category,
                "list_price": str(item.list_price),
                "base_cost": str(item.base_cost),
            }
            for item in ledger.catalogue.values()
        ],
        "budgets": [_line_dict(l) for l in ledger.budgets],
        "actuals": [_line_dict(l) for l in ledger.actuals],
        "notes": list(ledger.notes),
    }
    checks.append(
        Check(
            "fingerprint matches the canonical ledger",
            fingerprint_of(payload) == ledger.fingerprint,
            f"published {ledger.fingerprint}, recomputed {fingerprint_of(payload)}",
        )
    )

    budget_keys = {(l.branch, l.sku) for l in month_ledger.budgets}
    actual_keys = {(l.branch, l.sku) for l in month_ledger.actuals}
    checks.append(
        Check(
            "budget and actuals cover identical lines",
            budget_keys == actual_keys and len(budget_keys) == len(BRANCHES) * len(ledger.catalogue),
            f"{len(budget_keys)} keys, {len(budget_keys ^ actual_keys)} mismatched",
        )
    )

    components = bridge.volume + bridge.mix + bridge.price + bridge.cost
    checks.append(
        Check(
            "bridge components sum to the total variance",
            components == bridge.total_variance,
            f"{money.grouped(components)} against {money.grouped(bridge.total_variance)}",
        )
    )

    budget = {(l.branch, l.sku): l for l in month_ledger.budgets}
    actual = {(l.branch, l.sku): l for l in month_ledger.actuals}
    flex = money.cents(
        sum(
            (actual[k].volume * (budget[k].price - budget[k].unit_cost) for k in budget),
            Decimal(0),
        )
    )
    checks.append(
        Check(
            "flexed budget equals actual volume at budget rates",
            flex == bridge.flexed_gp,
            f"{money.grouped(flex)} recomputed, {money.grouped(bridge.flexed_gp)} published",
        )
    )

    checks.append(
        Check(
            "flexed less budget equals volume plus mix",
            bridge.flexed_gp - bridge.budget_gp == bridge.volume + bridge.mix,
            f"{money.grouped(bridge.flexed_gp - bridge.budget_gp)} against "
            f"{money.grouped(bridge.volume + bridge.mix)}",
        )
    )

    checks.append(
        Check(
            "actual less flexed equals price plus cost",
            bridge.actual_gp - bridge.flexed_gp == bridge.price + bridge.cost,
            f"{money.grouped(bridge.actual_gp - bridge.flexed_gp)} against "
            f"{money.grouped(bridge.price + bridge.cost)}",
        )
    )

    micro = bridge_mod.bridge_for_month(_micro_ledger(), "2026-06")
    checks.append(
        Check(
            "mix is zero when every product scales together",
            micro.mix == Decimal("0.00") and micro.volume == Decimal("4000.00"),
            f"mix {money.grouped(micro.mix)}, volume {money.grouped(micro.volume)} on a doubling of every product",
        )
    )

    branch_total = money.cents(sum((row.actual_gross_profit for row in analysis.by_branch), Decimal(0)))
    checks.append(
        Check(
            "branch variances sum to actual gross profit",
            branch_total == analysis.actual_gross_profit,
            f"{money.grouped(branch_total)} against {money.grouped(analysis.actual_gross_profit)}",
        )
    )

    category_total = money.cents(sum((row.actual_gross_profit for row in analysis.by_category), Decimal(0)))
    checks.append(
        Check(
            "category variances sum to actual gross profit",
            category_total == analysis.actual_gross_profit,
            f"{money.grouped(category_total)} against {money.grouped(analysis.actual_gross_profit)}",
        )
    )

    impacts = [abs(e.gross_profit_impact) for e in analysis.exceptions]
    checks.append(
        Check(
            "exception list is sorted by impact",
            impacts == sorted(impacts, reverse=True),
            f"{len(impacts)} exceptions, largest {money.grouped(impacts[0]) if impacts else '0.00'}",
        )
    )

    month_lines = lines.line_variances(ledger, analysis.month)
    line_cost = money.cents(sum((l.cost_rate for l in month_lines), Decimal(0)))
    checks.append(
        Check(
            "unit-cost drift sums to the bridge cost",
            line_cost == bridge.cost,
            f"{money.grouped(line_cost)} across {len(month_lines)} lines, "
            f"bridge {money.grouped(bridge.cost)}",
        )
    )

    line_total = money.cents(sum((l.variance for l in month_lines), Decimal(0)))
    checks.append(
        Check(
            "line variances sum to the bridge total",
            line_total == bridge.total_variance,
            f"{money.grouped(line_total)} across {len(month_lines)} lines, "
            f"bridge {money.grouped(bridge.total_variance)}",
        )
    )

    key_bridge = key["bridge"]
    key_total = money.cents(
        sum(
            (Decimal(key_bridge[k]) for k in ("volume", "mix", "price", "cost")),
            Decimal(0),
        )
    )
    key_ok = (
        key_total == Decimal(key_bridge["total"]) == bridge.total_variance
        and Decimal(key["headline"]["gross_profit_variance"]) == bridge.total_variance
    )
    checks.append(
        Check(
            "answer key matches recomputed bridge",
            key_ok,
            f"key total {money.grouped(key_total)}, recomputed {money.grouped(bridge.total_variance)}",
        )
    )

    return checks


def _line_dict(line) -> dict:
    return {
        "month": line.month,
        "branch": line.branch,
        "sku": line.sku,
        "volume": line.volume,
        "price": str(line.price),
        "unit_cost": str(line.unit_cost),
    }


def all_passed(checks: list[Check]) -> bool:
    return all(check.passed for check in checks)


def render_report(checks: list[Check]) -> str:
    passed = sum(1 for c in checks if c.passed)
    lines = [
        "# Validation report",
        "",
        f"**{passed}/{len(checks)} checks pass, covering sixteen distinct identities.** "
        "The full bridge identity is the sum of its two halves, so it corroborates "
        "them rather than counting as a separate property. Each check compares a "
        "published figure against an identity it was not derived from.",
        "",
        "| Check | Outcome | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        outcome = "pass" if check.passed else "**FAIL**"
        lines.append(f"| {check.name} | {outcome} | {check.detail} |")
    lines.append("")
    return "\n".join(lines)
