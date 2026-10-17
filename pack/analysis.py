"""One month assembled: headline, bridge, branch and category splits, exceptions.

This module composes the rules; it does no arithmetic of its own beyond summing
the ledger's published lines. Change the bridge, the line rule, the trend rule or
exception selection and this file does not move.
"""

from dataclasses import dataclass
from decimal import Decimal

from . import bridge as bridge_mod
from . import exceptions as exceptions_mod
from . import money
from .exceptions import ExceptionLine
from .model import Ledger


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
        return money.cents(self.variance / self.budget_gross_profit * 100)


@dataclass(frozen=True)
class MonthAnalysis:
    month: str
    budget_revenue: Decimal
    actual_revenue: Decimal
    budget_gross_profit: Decimal
    actual_gross_profit: Decimal
    bridge: bridge_mod.Bridge
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
        return money.cents(self.gross_profit_variance / self.budget_gross_profit * 100)

    @property
    def largest_driver(self) -> str:
        return max(self.bridge.components, key=lambda k: abs(self.bridge.components[k]))


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
        rows.append(GroupVariance(label, money.cents(b), money.cents(a)))
    return tuple(rows)


def by_branch(ledger: Ledger, month: str) -> tuple[GroupVariance, ...]:
    return _group(ledger, month, lambda branch, sku, ledger: branch)


def by_category(ledger: Ledger, month: str) -> tuple[GroupVariance, ...]:
    return _group(ledger, month, lambda branch, sku, ledger: ledger.category_of(sku))


def analyse_month(
    ledger: Ledger, month: str, materiality: Decimal = exceptions_mod.DEFAULT_MATERIALITY
) -> MonthAnalysis:
    month_ledger = ledger.month(month)
    budget_revenue = sum((l.revenue for l in month_ledger.budgets), Decimal(0))
    actual_revenue = sum((l.revenue for l in month_ledger.actuals), Decimal(0))
    budget_gp = sum((l.gross_profit for l in month_ledger.budgets), Decimal(0))
    actual_gp = sum((l.gross_profit for l in month_ledger.actuals), Decimal(0))

    return MonthAnalysis(
        month=month,
        budget_revenue=money.cents(budget_revenue),
        actual_revenue=money.cents(actual_revenue),
        budget_gross_profit=money.cents(budget_gp),
        actual_gross_profit=money.cents(actual_gp),
        bridge=bridge_mod.bridge_for_month(ledger, month),
        by_branch=by_branch(ledger, month),
        by_category=by_category(ledger, month),
        exceptions=exceptions_mod.select_exceptions(ledger, month, materiality),
        materiality=materiality,
    )
