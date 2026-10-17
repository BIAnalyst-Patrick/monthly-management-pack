"""Flexed budget, the gross-profit bridge and owner attribution.

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

``paired_lines`` is the one place that proves budget and actuals cover the same
product lines, so no downstream rule has to re-check it.
"""

from dataclasses import dataclass
from decimal import Decimal

from . import money
from .model import Ledger

OWNER_OF_COMPONENT = {
    "volume": "Branch Sales",
    "price": "Commercial / Pricing",
    "mix": "Category Management",
    "cost": "Procurement",
}


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


def paired_lines(ledger: Ledger, month: str):
    """The month's budget and actual lines, keyed identically or not at all."""
    month_ledger = ledger.month(month)
    budget = {(l.branch, l.sku): l for l in month_ledger.budgets}
    actual = {(l.branch, l.sku): l for l in month_ledger.actuals}
    if budget.keys() != actual.keys():
        raise ValueError(f"budget and actuals do not cover the same lines in {month}")
    keys = sorted(budget)
    return budget, actual, keys


def flexed_gross_profit(ledger: Ledger, month: str) -> Decimal:
    """Gross profit at actual volume and budget price and cost."""
    budget, actual, keys = paired_lines(ledger, month)
    return money.cents(
        sum((actual[key].volume * budget[key].unit_margin for key in keys), Decimal(0))
    )


def bridge_for_month(ledger: Ledger, month: str) -> Bridge:
    budget, actual, keys = paired_lines(ledger, month)

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
        budget_gp=money.cents(budget_gp),
        flexed_gp=money.cents(flexed),
        actual_gp=money.cents(actual_gp),
        volume=money.cents(volume),
        mix=money.cents(volume_and_mix - volume),
        price=money.cents(price),
        cost=money.cents(cost),
    )


def owner_totals(bridge: Bridge) -> dict[str, Decimal]:
    """Attribute each component to the department that can act on it."""
    totals = {owner: Decimal("0") for owner in OWNER_OF_COMPONENT.values()}
    for component, value in bridge.components.items():
        totals[OWNER_OF_COMPONENT[component]] += value
    return {owner: money.cents(value) for owner, value in totals.items()}
