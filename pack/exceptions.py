"""Which variances become exceptions, and the facts each one carries.

Selection is arithmetic: price erosion on the volume actually sold, a category
cost step, a branch persistently behind on units, and one portfolio-level mix
finding. The sentences that explain a finding are not built here; ``render``
owns them and reads ``evidence``.

``evidence`` is keyed by ``driver``:

    price   branch, erosion_pct, revenue_budget
    volume  branch, window, adverse_months, variance_pct
    cost    step_pct
    mix     mover, budget_share_pct, actual_share_pct
"""

from dataclasses import dataclass, field
from decimal import Decimal

from . import money
from .bridge import OWNER_OF_COMPONENT, paired_lines
from .model import BRANCHES, CATEGORIES, Ledger
from .trends import branch_trends

DEFAULT_MATERIALITY = Decimal("10000")

PRICE_EROSION_THRESHOLD = Decimal("0.975")
COST_STEP_THRESHOLD = Decimal("1.025")


@dataclass(frozen=True)
class ExceptionLine:
    scope: str
    label: str
    driver: str
    gross_profit_impact: Decimal
    owner: str
    evidence: dict = field(default_factory=dict)


def _price_findings(budget, actual, keys):
    found = []
    for branch in BRANCHES:
        branch_keys = [k for k in keys if k[0] == branch]
        actual_value = sum(
            (actual[k].volume * actual[k].price for k in branch_keys), Decimal(0)
        )
        budget_value = sum(
            (actual[k].volume * budget[k].price for k in branch_keys), Decimal(0)
        )
        revenue_budget = sum((budget[k].revenue for k in branch_keys), Decimal(0))

        if budget_value and actual_value / budget_value < PRICE_EROSION_THRESHOLD:
            impact = actual_value - budget_value
            erosion = (1 - actual_value / budget_value) * 100
            found.append(
                ExceptionLine(
                    scope="branch",
                    label=branch,
                    driver="price",
                    gross_profit_impact=money.cents(impact),
                    owner=OWNER_OF_COMPONENT["price"],
                    evidence={
                        "branch": branch,
                        "erosion_pct": erosion,
                        "revenue_budget": revenue_budget,
                    },
                )
            )
    return found


def _trend_findings(ledger: Ledger, month: str):
    found = []
    for trend in branch_trends(ledger, month):
        if not trend.is_off_track:
            continue
        window = f"{len(trend.window)} months"
        found.append(
            ExceptionLine(
                scope="branch",
                label=f"{trend.branch} ({window})",
                driver="volume",
                gross_profit_impact=money.cents(trend.volume_effect),
                owner=OWNER_OF_COMPONENT["volume"],
                evidence={
                    "branch": trend.branch,
                    "window": window,
                    "adverse_months": trend.adverse_months,
                    "variance_pct": trend.variance_pct,
                },
            )
        )
    return found


def _cost_findings(ledger: Ledger, budget, actual, keys):
    found = []
    for category in CATEGORIES:
        category_keys = [k for k in keys if ledger.category_of(k[1]) == category]
        cost_actual = sum(
            (actual[k].volume * actual[k].unit_cost for k in category_keys), Decimal(0)
        )
        cost_budget = sum(
            (actual[k].volume * budget[k].unit_cost for k in category_keys), Decimal(0)
        )
        if cost_budget and cost_actual / cost_budget > COST_STEP_THRESHOLD:
            impact = cost_budget - cost_actual
            step = (cost_actual / cost_budget - 1) * 100
            found.append(
                ExceptionLine(
                    scope="category",
                    label=category,
                    driver="cost",
                    gross_profit_impact=money.cents(impact),
                    owner=OWNER_OF_COMPONENT["cost"],
                    evidence={"step_pct": step},
                )
            )
    return found


def _mix_finding(ledger: Ledger, budget, actual, keys, materiality: Decimal):
    units_budget = Decimal(sum(budget[k].volume for k in keys))
    units_actual = Decimal(sum(actual[k].volume for k in keys))
    scale = units_actual / units_budget if units_budget else Decimal(1)

    # One aggregate mix finding: the blend change is a portfolio-level effect,
    # and splitting it by category would report the same shilling twice.
    mix_impact = sum(
        ((Decimal(actual[k].volume) - scale * Decimal(budget[k].volume)) * budget[k].unit_margin
         for k in keys),
        Decimal(0),
    )
    shares = {}
    for category in CATEGORIES:
        category_keys = [k for k in keys if ledger.category_of(k[1]) == category]
        cat_budget = Decimal(sum(budget[k].volume for k in category_keys))
        cat_actual = Decimal(sum(actual[k].volume for k in category_keys))
        shares[category] = (cat_budget / units_budget, cat_actual / units_actual)
    mover = max(shares, key=lambda c: abs(shares[c][1] - shares[c][0]))
    moved_budget, moved_actual = shares[mover]

    if abs(mix_impact) >= materiality and units_budget:
        return ExceptionLine(
            scope="portfolio",
            label="Product mix",
            driver="mix",
            gross_profit_impact=money.cents(mix_impact),
            owner=OWNER_OF_COMPONENT["mix"],
            evidence={
                "mover": mover,
                "budget_share_pct": moved_budget * 100,
                "actual_share_pct": moved_actual * 100,
            },
        )
    return None


def select_exceptions(
    ledger: Ledger, month: str, materiality: Decimal = DEFAULT_MATERIALITY
) -> tuple[ExceptionLine, ...]:
    """Everything material enough to carry an owner and an action, largest first."""
    budget, actual, keys = paired_lines(ledger, month)

    found = []
    found += _price_findings(budget, actual, keys)
    found += _trend_findings(ledger, month)
    found += _cost_findings(ledger, budget, actual, keys)
    mix = _mix_finding(ledger, budget, actual, keys, materiality)
    if mix is not None:
        found.append(mix)

    filtered = [e for e in found if abs(e.gross_profit_impact) >= materiality]
    filtered.sort(key=lambda e: (-abs(e.gross_profit_impact), e.label, e.driver))
    return tuple(filtered)
