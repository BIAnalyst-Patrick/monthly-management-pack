"""Flexed budget, gross-profit bridge, owner attribution and exceptions.

The bridge decomposes the gross-profit variance into four components that sum
exactly to the total:

    volume  total units, valued at the budget gross profit per unit
    mix     the part of the volume movement that is not explained by total
            units - i.e. selling a different product blend at budget margins
    price   actual units at the change in selling price
    cost    actual units at the change in unit cost

``volume`` is computed first and ``mix`` is the residual of the volume-and-mix
movement, so the four components reconcile to the cent by construction rather
than by rounding luck.
"""

from dataclasses import dataclass
from decimal import Decimal

from .model import BRANCHES, CATEGORIES, Ledger

CENT = Decimal("0.01")

COMPONENT_ORDER = ("volume", "mix", "price", "cost")

OWNER_OF_COMPONENT = {
    "volume": "Branch Sales",
    "price": "Commercial / Pricing",
    "mix": "Category Management",
    "cost": "Procurement",
}

DEFAULT_MATERIALITY = Decimal("10000")

PRICE_EROSION_THRESHOLD = Decimal("0.975")
COST_STEP_THRESHOLD = Decimal("1.025")
VOLUME_MISS_THRESHOLD = Decimal("0.95")


def _money(value) -> Decimal:
    return Decimal(value).quantize(CENT)


@dataclass(frozen=True)
class Bridge:
    month: str
    budget_gp: Decimal
    flexed_gp: Decimal
    actual_gp: Decimal
    volume: Decimal
    mix: Decimal
    price: Decimal
    cost: Decimal

    @property
    def total_variance(self) -> Decimal:
        return self.actual_gp - self.budget_gp

    @property
    def components(self) -> dict[str, Decimal]:
        return {
            "volume": self.volume,
            "mix": self.mix,
            "price": self.price,
            "cost": self.cost,
        }


@dataclass(frozen=True)
class GroupVariance:
    label: str
    budget_gross_profit: Decimal
    actual_gross_profit: Decimal

    @property
    def variance(self) -> Decimal:
        return self.actual_gross_profit - self.budget_gross_profit

    @property
    def variance_pct(self) -> Decimal:
        if self.budget_gross_profit == 0:
            return Decimal("0")
        return (self.variance / self.budget_gross_profit * 100).quantize(CENT)


@dataclass(frozen=True)
class ExceptionLine:
    scope: str
    label: str
    driver: str
    gross_profit_impact: Decimal
    owner: str
    action: str
    finding: str


@dataclass(frozen=True)
class MonthAnalysis:
    month: str
    budget_revenue: Decimal
    actual_revenue: Decimal
    budget_gross_profit: Decimal
    actual_gross_profit: Decimal
    bridge: Bridge
    by_branch: tuple[GroupVariance, ...]
    by_category: tuple[GroupVariance, ...]
    exceptions: tuple[ExceptionLine, ...]
    materiality: Decimal

    @property
    def gross_profit_variance(self) -> Decimal:
        return self.actual_gross_profit - self.budget_gross_profit

    @property
    def variance_pct(self) -> Decimal:
        if self.budget_gross_profit == 0:
            return Decimal("0")
        return (self.gross_profit_variance / self.budget_gross_profit * 100).quantize(CENT)

    @property
    def largest_driver(self) -> str:
        return max(self.bridge.components, key=lambda k: abs(self.bridge.components[k]))


def _paired(ledger: Ledger, month: str):
    month_ledger = ledger.month(month)
    budget = {(l.branch, l.sku): l for l in month_ledger.budgets}
    actual = {(l.branch, l.sku): l for l in month_ledger.actuals}
    if budget.keys() != actual.keys():
        raise ValueError(f"budget and actuals do not cover the same lines in {month}")
    keys = sorted(budget)
    return budget, actual, keys


def flexed_gross_profit(ledger: Ledger, month: str) -> Decimal:
    """Gross profit at actual volume and budget price and cost."""
    budget, actual, keys = _paired(ledger, month)
    return _money(
        sum((actual[key].volume * budget[key].unit_margin for key in keys), Decimal(0))
    )


def bridge_for_month(ledger: Ledger, month: str) -> Bridge:
    budget, actual, keys = _paired(ledger, month)

    budget_gp = sum((budget[k].gross_profit for k in keys), Decimal(0))
    actual_gp = sum((actual[k].gross_profit for k in keys), Decimal(0))
    flexed = sum((actual[k].volume * budget[k].unit_margin for k in keys), Decimal(0))

    budget_units = sum(budget[k].volume for k in keys)
    actual_units = sum(actual[k].volume for k in keys)

    volume_and_mix = sum(
        ((actual[k].volume - budget[k].volume) * budget[k].unit_margin for k in keys),
        Decimal(0),
    )

    # Total units, valued at the budget's gross profit per unit.
    gp_per_unit = budget_gp / Decimal(budget_units)
    volume = (Decimal(actual_units) - Decimal(budget_units)) * gp_per_unit

    price = sum(
        (actual[k].volume * (actual[k].price - budget[k].price) for k in keys),
        Decimal(0),
    )
    cost = sum(
        (actual[k].volume * (budget[k].unit_cost - actual[k].unit_cost) for k in keys),
        Decimal(0),
    )

    return Bridge(
        month=month,
        budget_gp=_money(budget_gp),
        flexed_gp=_money(flexed),
        actual_gp=_money(actual_gp),
        volume=_money(volume),
        mix=_money(volume_and_mix - volume),
        price=_money(price),
        cost=_money(cost),
    )


def owner_totals(bridge: Bridge) -> dict[str, Decimal]:
    """Attribute each component to the department that can act on it."""
    totals = {owner: Decimal("0") for owner in OWNER_OF_COMPONENT.values()}
    for component, value in bridge.components.items():
        totals[OWNER_OF_COMPONENT[component]] += value
    return {owner: _money(value) for owner, value in totals.items()}


def _group(ledger: Ledger, month: str, key):
    month_ledger = ledger.month(month)
    budget = {(l.branch, l.sku): l for l in month_ledger.budgets}
    actual = {(l.branch, l.sku): l for l in month_ledger.actuals}
    labels = sorted({key(branch, sku, ledger) for branch, sku in budget})
    rows = []
    for label in labels:
        b = sum(
            (budget[(br, sku)].gross_profit for br, sku in budget
             if key(br, sku, ledger) == label),
            Decimal(0),
        )
        a = sum(
            (actual[(br, sku)].gross_profit for br, sku in actual
             if key(br, sku, ledger) == label),
            Decimal(0),
        )
        rows.append(GroupVariance(label, _money(b), _money(a)))
    return tuple(rows)


def by_branch(ledger: Ledger, month: str) -> tuple[GroupVariance, ...]:
    return _group(ledger, month, lambda branch, sku, ledger: branch)


def by_category(ledger: Ledger, month: str) -> tuple[GroupVariance, ...]:
    return _group(ledger, month, lambda branch, sku, ledger: ledger.category_of(sku))


def _exceptions(ledger: Ledger, month: str, materiality: Decimal):
    month_ledger = ledger.month(month)
    budget = {(l.branch, l.sku): l for l in month_ledger.budgets}
    actual = {(l.branch, l.sku): l for l in month_ledger.actuals}
    keys = sorted(budget)

    found: list[ExceptionLine] = []

    for branch in BRANCHES:
        branch_keys = [k for k in keys if k[0] == branch]
        actual_value = sum(
            (actual[k].volume * actual[k].price for k in branch_keys), Decimal(0)
        )
        budget_value = sum(
            (actual[k].volume * budget[k].price for k in branch_keys), Decimal(0)
        )
        revenue_budget = sum((budget[k].revenue for k in branch_keys), Decimal(0))
        gp_budget = sum((budget[k].gross_profit for k in branch_keys), Decimal(0))
        units_actual = sum(actual[k].volume for k in branch_keys)
        units_budget = sum(budget[k].volume for k in branch_keys)

        if budget_value and actual_value / budget_value < PRICE_EROSION_THRESHOLD:
            impact = actual_value - budget_value
            erosion = (1 - actual_value / budget_value) * 100
            found.append(
                ExceptionLine(
                    scope="branch",
                    label=branch,
                    driver="price",
                    gross_profit_impact=_money(impact),
                    owner=OWNER_OF_COMPONENT["price"],
                    action=f"Reissue the {branch} price file and cap discount authority at 7%",
                    finding=(
                        f"Prices realised {erosion.quantize(CENT)}% below the budgeted "
                        f"price for the volume actually sold, costing "
                        f"{_format_money(-impact)} of gross profit on "
                        f"{_format_money(revenue_budget)} of budgeted branch revenue."
                    ),
                )
            )

        if units_budget and Decimal(units_actual) / Decimal(units_budget) < VOLUME_MISS_THRESHOLD:
            gp_per_unit = gp_budget / Decimal(units_budget)
            impact = (Decimal(units_actual) - Decimal(units_budget)) * gp_per_unit
            shortfall = (
                (Decimal(units_actual) / Decimal(units_budget) - 1) * 100
            ).quantize(CENT)
            found.append(
                ExceptionLine(
                    scope="branch",
                    label=branch,
                    driver="volume",
                    gross_profit_impact=_money(impact),
                    owner=OWNER_OF_COMPONENT["volume"],
                    action=f"Rebuild the {branch} trading plan against the volume gap",
                    finding=(
                        f"Units sold ran {abs(shortfall)}% below budget, which at the "
                        f"budgeted gross profit per unit is {_format_money(-impact)} "
                        f"of gross profit."
                    ),
                )
            )

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
                    gross_profit_impact=_money(impact),
                    owner=OWNER_OF_COMPONENT["cost"],
                    action=f"Renegotiate {category} supply terms or reprice the range",
                    finding=(
                        f"Unit costs on {category} are running {step.quantize(CENT)}% "
                        f"above budget on the volume bought, costing "
                        f"{_format_money(-impact)} of gross profit."
                    ),
                )
            )

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
        found.append(
            ExceptionLine(
                scope="portfolio",
                label="Product mix",
                driver="mix",
                gross_profit_impact=_money(mix_impact),
                owner=OWNER_OF_COMPONENT["mix"],
                action=(
                    f"Review {mover} ranging, promo depth and shelf allocation "
                    "against the budgeted blend"
                ),
                finding=(
                    f"The blend moved towards lower-margin lines: {mover} went from "
                    f"{(moved_budget * 100).quantize(CENT)}% of budgeted units to "
                    f"{(moved_actual * 100).quantize(CENT)}% actual, costing "
                    f"{_format_money(-mix_impact)} of gross profit at budget margins."
                ),
            )
        )

    filtered = [e for e in found if abs(e.gross_profit_impact) >= materiality]
    filtered.sort(key=lambda e: (-abs(e.gross_profit_impact), e.label, e.driver))
    return tuple(filtered)


def _format_money(value: Decimal) -> str:
    return f"KES {abs(value):,.2f}"


def analyse_month(
    ledger: Ledger, month: str, materiality: Decimal = DEFAULT_MATERIALITY
) -> MonthAnalysis:
    month_ledger = ledger.month(month)
    budget_revenue = sum((l.revenue for l in month_ledger.budgets), Decimal(0))
    actual_revenue = sum((l.revenue for l in month_ledger.actuals), Decimal(0))
    budget_gp = sum((l.gross_profit for l in month_ledger.budgets), Decimal(0))
    actual_gp = sum((l.gross_profit for l in month_ledger.actuals), Decimal(0))

    return MonthAnalysis(
        month=month,
        budget_revenue=_money(budget_revenue),
        actual_revenue=_money(actual_revenue),
        budget_gross_profit=_money(budget_gp),
        actual_gross_profit=_money(actual_gp),
        bridge=bridge_for_month(ledger, month),
        by_branch=by_branch(ledger, month),
        by_category=by_category(ledger, month),
        exceptions=_exceptions(ledger, month, materiality),
        materiality=materiality,
    )


def trend(ledger: Ledger, months: tuple[str, ...] | None = None) -> tuple[dict, ...]:
    """Month-by-month gross profit against budget, for the trend table."""
    rows = []
    for month in months or ledger.months:
        month_ledger = ledger.month(month)
        budget_gp = sum((l.gross_profit for l in month_ledger.budgets), Decimal(0))
        actual_gp = sum((l.gross_profit for l in month_ledger.actuals), Decimal(0))
        rows.append(
            {
                "month": month,
                "budget_gross_profit": _money(budget_gp),
                "actual_gross_profit": _money(actual_gp),
                "variance": _money(actual_gp - budget_gp),
            }
        )
    return tuple(rows)
