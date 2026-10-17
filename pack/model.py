"""Domain model: the catalogue, ledger lines, and the parsed ledger.

Money is held as Decimal so that every variance component reconciles exactly
to the total instead of drifting by float cents.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from . import money

BRANCHES = ("Nairobi CBD", "Nakuru", "Mombasa Road")
CATEGORIES = ("Home Care", "Beverages", "Staples", "Snacks")
SKUS_PER_CATEGORY = 10
SEED = 20260101

MONTHS = tuple(
    f"{year}-{month:02d}"
    for year in (2025, 2026)
    for month in range(1, 13)
    if not (year == 2026 and month > 6)
)


def to_money(value) -> Decimal:
    """Quantise to cents, half-up, the way an invoice would."""
    return money.cents(value)


@dataclass(frozen=True)
class CatalogueItem:
    sku: str
    name: str
    category: str
    list_price: Decimal
    base_cost: Decimal

    @property
    def gross_margin_pct(self) -> Decimal:
        return (self.list_price - self.base_cost) / self.list_price * 100


@dataclass(frozen=True)
class Line:
    """One month of one product in one branch."""

    month: str
    branch: str
    sku: str
    volume: int
    price: Decimal
    unit_cost: Decimal

    @property
    def revenue(self) -> Decimal:
        return self.price * self.volume

    @property
    def cost_of_sales(self) -> Decimal:
        return self.unit_cost * self.volume

    @property
    def gross_profit(self) -> Decimal:
        return self.revenue - self.cost_of_sales

    @property
    def unit_margin(self) -> Decimal:
        return self.price - self.unit_cost


@dataclass(frozen=True)
class Ledger:
    seed: int
    fingerprint: str
    months: tuple[str, ...]
    branches: tuple[str, ...]
    catalogue: Mapping[str, CatalogueItem]
    budgets: tuple[Line, ...]
    actuals: tuple[Line, ...]
    notes: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: Mapping) -> "Ledger":
        catalogue = {
            item["sku"]: CatalogueItem(
                sku=item["sku"],
                name=item["name"],
                category=item["category"],
                list_price=Decimal(item["list_price"]),
                base_cost=Decimal(item["base_cost"]),
            )
            for item in raw["catalogue"]
        }

        def parse(rows):
            return tuple(
                Line(
                    month=row["month"],
                    branch=row["branch"],
                    sku=row["sku"],
                    volume=int(row["volume"]),
                    price=Decimal(row["price"]),
                    unit_cost=Decimal(row["unit_cost"]),
                )
                for row in rows
            )

        return cls(
            seed=raw["seed"],
            fingerprint=raw["fingerprint"],
            months=tuple(raw["months"]),
            branches=tuple(raw["branches"]),
            catalogue=catalogue,
            budgets=parse(raw["budgets"]),
            actuals=parse(raw["actuals"]),
            notes=tuple(raw["notes"]),
        )

    def category_of(self, sku: str) -> str:
        return self.catalogue[sku].category

    def month(self, month: str) -> "MonthLedger":
        if month not in self.months:
            raise KeyError(f"{month} is not in this ledger")
        budgets = [l for l in self.budgets if l.month == month]
        actuals = [l for l in self.actuals if l.month == month]
        return MonthLedger(month=month, budgets=budgets, actuals=actuals)


@dataclass(frozen=True)
class MonthLedger:
    month: str
    budgets: tuple[Line, ...]
    actuals: tuple[Line, ...]
