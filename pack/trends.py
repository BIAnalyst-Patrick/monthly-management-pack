"""The branch trend rule: units over a trailing window, not one month.

A branch is off track when it is below budget on units in at least two of the
last three months and its rolling unit gap is at least 5% of budget gross
profit. Reading units rather than gross profit matters: a branch discounting its
way to a profit miss has a pricing problem and must not be reported as a branch
that cannot trade.
"""

from dataclasses import dataclass
from decimal import Decimal

from . import money
from .model import Ledger

TREND_WINDOW = 3
TREND_ADVERSE_MONTHS = 2
TREND_VARIANCE_THRESHOLD = Decimal("0.05")


@dataclass(frozen=True)
class BranchTrend:
    """A branch's units against budget over a trailing window."""

    branch: str
    window: tuple[str, ...]
    units_budget: int
    units_actual: int
    budget_gp: Decimal
    actual_gp: Decimal
    adverse_months: int

    @property
    def volume_effect(self) -> Decimal:
        """The unit gap over the window, valued at the budget margin per unit."""
        if not self.units_budget:
            return Decimal("0.00")
        return money.cents(
            Decimal(self.units_actual - self.units_budget)
            * (self.budget_gp / Decimal(self.units_budget))
        )

    @property
    def variance_pct(self) -> Decimal:
        if self.budget_gp == 0:
            return Decimal("0")
        return money.cents(self.volume_effect / self.budget_gp * 100)

    @property
    def is_off_track(self) -> bool:
        """Persistently behind on units, rather than one bad month."""
        return (
            self.adverse_months >= TREND_ADVERSE_MONTHS
            and self.budget_gp > 0
            and -self.variance_pct / 100 >= TREND_VARIANCE_THRESHOLD
        )


def branch_trends(
    ledger: Ledger, month: str, window: int = TREND_WINDOW
) -> tuple[BranchTrend, ...]:
    """Trailing-window units and gross profit per branch, ending at ``month``."""
    if month not in ledger.months:
        raise KeyError(f"{month} is not in this ledger")
    end = ledger.months.index(month)
    months = ledger.months[max(0, end - window + 1): end + 1]

    trends = []
    for branch in ledger.branches:
        budget_gp = Decimal(0)
        actual_gp = Decimal(0)
        units_budget = 0
        units_actual = 0
        adverse = 0
        for covered in months:
            month_ledger = ledger.month(covered)
            month_budget = [l for l in month_ledger.budgets if l.branch == branch]
            month_actual = [l for l in month_ledger.actuals if l.branch == branch]
            b_units = sum(l.volume for l in month_budget)
            a_units = sum(l.volume for l in month_actual)
            budget_gp += sum((l.gross_profit for l in month_budget), Decimal(0))
            actual_gp += sum((l.gross_profit for l in month_actual), Decimal(0))
            units_budget += b_units
            units_actual += a_units
            if a_units < b_units:
                adverse += 1
        trends.append(
            BranchTrend(
                branch=branch,
                window=months,
                units_budget=units_budget,
                units_actual=units_actual,
                budget_gp=money.cents(budget_gp),
                actual_gp=money.cents(actual_gp),
                adverse_months=adverse,
            )
        )
    return tuple(trends)


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
                "budget_gross_profit": money.cents(budget_gp),
                "actual_gross_profit": money.cents(actual_gp),
                "variance": money.cents(actual_gp - budget_gp),
            }
        )
    return tuple(rows)
