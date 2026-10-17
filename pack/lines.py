"""Per-line decomposition: every product in every branch, split four ways.

Price and unit-cost drift are valued at the volume actually sold, which is what
separates a rate problem from a volume problem; the two volume halves are the
volume change valued at budget rates. The four parts sum to the line's variance
to the cent, and the aggregate of each part agrees with the bridge.
"""

from dataclasses import dataclass
from decimal import Decimal

from . import money
from .bridge import OWNER_OF_COMPONENT, paired_lines
from .model import Ledger


@dataclass(frozen=True)
class LineVariance:
    """One product in one branch for one month, decomposed exactly.

    ``price`` and ``cost_rate`` are valued at **actual** volume, which is what
    isolates unit-cost drift from the volume change; ``volume_revenue`` and
    ``volume_cost`` are the volume change valued at budget rates. The four sum
    to ``variance`` to the cent.
    """

    branch: str
    sku: str
    product: str
    category: str
    owner: str
    units_budget: int
    units_actual: int
    gp_budget: Decimal
    gp_actual: Decimal
    price: Decimal
    cost_rate: Decimal
    volume_revenue: Decimal
    volume_cost: Decimal

    @property
    def variance(self) -> Decimal:
        return self.gp_actual - self.gp_budget

    @property
    def volume(self) -> Decimal:
        return self.volume_revenue + self.volume_cost


def _owning_department(price, cost_rate, volume) -> str:
    """The department that can move the largest part of this line.

    Ties break price, then cost, then volume, so the assignment is stable for
    flat lines and for lines where two effects happen to be equal.
    """
    ranked = (("price", price), ("cost", cost_rate), ("volume", volume))
    best = max(range(len(ranked)), key=lambda i: (abs(ranked[i][1]), -i))
    return OWNER_OF_COMPONENT[ranked[best][0]]


def line_variances(ledger: Ledger, month: str) -> tuple[LineVariance, ...]:
    """Every product line, decomposed so the four parts sum to its variance."""
    budget, actual, keys = paired_lines(ledger, month)
    rows = []
    for key in keys:
        b, a = budget[key], actual[key]
        volume_change = Decimal(a.volume - b.volume)
        price = money.cents(a.volume * (a.price - b.price))
        cost_rate = money.cents(a.volume * (b.unit_cost - a.unit_cost))
        volume_revenue = money.cents(volume_change * b.price)
        volume_cost = money.cents(-volume_change * b.unit_cost)
        item = ledger.catalogue[a.sku]
        rows.append(
            LineVariance(
                branch=a.branch,
                sku=a.sku,
                product=item.name,
                category=item.category,
                owner=_owning_department(price, cost_rate, volume_revenue + volume_cost),
                units_budget=b.volume,
                units_actual=a.volume,
                gp_budget=money.cents(b.gross_profit),
                gp_actual=money.cents(a.gross_profit),
                price=price,
                cost_rate=cost_rate,
                volume_revenue=volume_revenue,
                volume_cost=volume_cost,
            )
        )
    rows.sort(key=lambda row: (-abs(row.variance), row.branch, row.sku))
    return tuple(rows)
