"""Per-line decomposition, per-line ownership, and the branch trend rule.

Written before the code. Both pieces are arithmetic identities that a wrong
implementation can satisfy at the aggregate level, so each component is pinned
against a case small enough to work out by hand.
"""

import unittest
from decimal import Decimal

from pack import generator, render
from pack.analysis import analyse_month
from pack.bridge import OWNER_OF_COMPONENT, bridge_for_month
from pack.lines import line_variances
from pack.trends import branch_trends
from pack.model import Ledger

D = Decimal


def make_ledger(months, budget, actual, catalogue=None):
    """``budget``/``actual`` map ``(month, sku)`` to ``(volume, price, cost)``."""
    catalogue = catalogue or [
        {"sku": "A", "name": "Product A", "category": "Home Care",
         "list_price": "100.00", "base_cost": "70.00"},
        {"sku": "B", "name": "Product B", "category": "Staples",
         "list_price": "100.00", "base_cost": "90.00"},
    ]

    def rows(source):
        return [
            {
                "month": month,
                "branch": "Nairobi CBD",
                "sku": sku,
                "volume": volume,
                "price": price,
                "unit_cost": cost,
            }
            for (month, sku), (volume, price, cost) in sorted(source.items())
        ]

    return Ledger.from_dict(
        {
            "seed": 1,
            "fingerprint": "0" * 16,
            "months": list(months),
            "branches": ["Nairobi CBD"],
            "catalogue": catalogue,
            "budgets": rows(budget),
            "actuals": rows(actual),
            "notes": ["synthetic"],
        }
    )


def one_month(budget, actual, months=("2026-06",)):
    return make_ledger(months, {("2026-06", "A"): budget}, {("2026-06", "A"): actual})


class LineSumTest(unittest.TestCase):
    def test_components_sum_to_the_line_variance(self):
        ledger = one_month((100, "100.00", "70.00"), (120, "95.00", "72.00"))
        line = line_variances(ledger, "2026-06")[0]
        self.assertEqual(
            line.price + line.cost_rate + line.volume_revenue + line.volume_cost,
            line.variance,
        )

    def test_one_row_per_branch_and_sku(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        lines = line_variances(ledger, "2026-06")
        self.assertEqual(len(lines), 3 * 40)

    def test_every_line_closes_on_the_generated_ledger(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        for line in line_variances(ledger, "2026-06"):
            self.assertEqual(
                line.price + line.cost_rate + line.volume_revenue + line.volume_cost,
                line.variance,
                line.sku,
            )


class LineComponentTest(unittest.TestCase):
    def test_price_is_actual_volume_at_the_price_change(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (120, "95.00", "70.00")), "2026-06"
        )[0]
        self.assertEqual(line.price, D("-600.00"))

    def test_cost_rate_is_actual_volume_at_the_cost_change(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (100, "100.00", "72.00")), "2026-06"
        )[0]
        self.assertEqual(line.cost_rate, D("-200.00"))

    def test_volume_splits_into_revenue_and_cost_at_budget_rates(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (120, "100.00", "70.00")), "2026-06"
        )[0]
        self.assertEqual(line.volume_revenue, D("2000.00"))
        self.assertEqual(line.volume_cost, D("-1400.00"))
        self.assertEqual(line.volume_revenue + line.volume_cost, line.volume)

    def test_a_flat_line_has_no_components(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (100, "100.00", "70.00")), "2026-06"
        )[0]
        self.assertEqual(
            line.price + line.cost_rate + line.volume_revenue + line.volume_cost,
            D("0.00"),
        )


class LineReconciliationTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger.from_dict(generator.build_ledger())
        self.lines = line_variances(self.ledger, "2026-06")
        self.bridge = bridge_for_month(self.ledger, "2026-06")

    def test_line_price_sums_to_the_bridge_price(self):
        self.assertEqual(
            sum((l.price for l in self.lines), D(0)), self.bridge.price
        )

    def test_line_cost_rate_sums_to_the_bridge_cost(self):
        self.assertEqual(
            sum((l.cost_rate for l in self.lines), D(0)), self.bridge.cost
        )

    def test_line_volume_sums_to_volume_plus_mix(self):
        self.assertEqual(
            sum((l.volume for l in self.lines), D(0)),
            self.bridge.volume + self.bridge.mix,
        )

    def test_line_totals_sum_to_the_bridge_total(self):
        self.assertEqual(
            sum((l.variance for l in self.lines), D(0)), self.bridge.total_variance
        )


class LineOwnershipTest(unittest.TestCase):
    def test_every_line_has_one_of_the_four_departments(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        owners = {l.owner for l in line_variances(ledger, "2026-06")}
        self.assertTrue(
            owners <= {"Branch Sales", "Commercial / Pricing",
                       "Category Management", "Procurement"},
            owners,
        )

    def test_a_cost_driven_line_belongs_to_procurement(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (100, "100.00", "95.00")), "2026-06"
        )[0]
        self.assertEqual(line.owner, "Procurement")

    def test_a_price_driven_line_belongs_to_pricing(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (100, "80.00", "70.00")), "2026-06"
        )[0]
        self.assertEqual(line.owner, "Commercial / Pricing")

    def test_a_volume_driven_line_belongs_to_branch_sales(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (150, "100.00", "70.00")), "2026-06"
        )[0]
        self.assertEqual(line.owner, "Branch Sales")

    def test_ownership_breaks_ties_deterministically(self):
        line = line_variances(
            one_month((100, "100.00", "70.00"), (100, "100.00", "70.00")), "2026-06"
        )[0]
        self.assertEqual(line.owner, OWNER_OF_COMPONENT["price"])


class BranchTrendTest(unittest.TestCase):
    """Three months at 100 units of a 30-margin product: budget GP 9,000."""

    MONTHS = ("2026-04", "2026-05", "2026-06")

    def _ledger(self, volumes):
        budget = {(m, "A"): (100, "100.00", "70.00") for m in self.MONTHS}
        actual = {
            (m, "A"): (v, "100.00", "70.00")
            for m, v in zip(self.MONTHS, volumes)
        }
        return make_ledger(self.MONTHS, budget, actual)

    def test_a_single_bad_month_is_not_a_trend(self):
        ledger = self._ledger([100, 100, 40])
        trend = branch_trends(ledger, "2026-06")[0]
        self.assertEqual(trend.adverse_months, 1)
        self.assertFalse(trend.is_off_track)

    def test_sustained_drift_is_a_trend(self):
        ledger = self._ledger([70, 70, 70])
        trend = branch_trends(ledger, "2026-06")[0]
        self.assertEqual(trend.adverse_months, 3)
        self.assertTrue(trend.is_off_track)

    def test_budget_behaviour_is_not_a_trend(self):
        ledger = self._ledger([100, 100, 100])
        trend = branch_trends(ledger, "2026-06")[0]
        self.assertFalse(trend.is_off_track)

    def test_the_window_totals_are_the_months_it_covers(self):
        ledger = self._ledger([70, 80, 90])
        trend = branch_trends(ledger, "2026-06")[0]
        self.assertEqual(trend.window, self.MONTHS)
        self.assertEqual(trend.actual_gp, D("7200.00"))
        self.assertEqual(trend.budget_gp, D("9000.00"))

    def test_the_window_is_trailing_not_forward(self):
        ledger = self._ledger([70, 70, 70])
        trend = branch_trends(ledger, "2026-04")[0]
        self.assertEqual(trend.window, ("2026-04",))

    def test_the_planted_branch_shortfall_is_off_track(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        trends = {t.branch: t for t in branch_trends(ledger, "2026-06")}
        self.assertTrue(trends["Mombasa Road"].is_off_track)
        self.assertFalse(trends["Nairobi CBD"].is_off_track)


class TrendExceptionTest(unittest.TestCase):
    def test_the_trend_rule_replaces_the_single_month_level_test(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        analysis = analyse_month(ledger, "2026-06")
        volume = [e for e in analysis.exceptions if e.driver == "volume"]
        self.assertEqual(len(volume), 1)
        self.assertIn("3 months", render.exception_finding(volume[0]))

    def test_a_single_bad_month_produces_no_volume_exception(self):
        months = ("2026-04", "2026-05", "2026-06")
        budget = {(m, "A"): (100, "100.00", "70.00") for m in months}
        actual = {
            ("2026-04", "A"): (100, "100.00", "70.00"),
            ("2026-05", "A"): (100, "100.00", "70.00"),
            ("2026-06", "A"): (30, "100.00", "70.00"),
        }
        ledger = make_ledger(months, budget, actual)
        analysis = analyse_month(ledger, "2026-06", materiality=D("0"))
        self.assertEqual([e for e in analysis.exceptions if e.driver == "volume"], [])


if __name__ == "__main__":
    unittest.main()
