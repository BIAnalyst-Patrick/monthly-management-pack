"""Tests for the flex and the gross-profit bridge, written before either exists.

The bridge is the component that must reconcile exactly: a plausible-looking
wrong decomposition still sums to something close, so these tests pin the
identities rather than the numbers.
"""

import unittest
from decimal import Decimal

from pack import generator, variance
from pack.model import BRANCHES, Ledger

D = Decimal


def micro_ledger(budget, actual):
    """Two SKUs, one branch, one month: small enough to reason about by hand.

    ``budget`` and ``actual`` are ``{sku: (volume, price, cost)}``.
    """
    catalogue = [
        {
            "sku": "A",
            "name": "Product A",
            "category": "Home Care",
            "list_price": "100.00",
            "base_cost": "70.00",
        },
        {
            "sku": "B",
            "name": "Product B",
            "category": "Staples",
            "list_price": "100.00",
            "base_cost": "90.00",
        },
    ]
    rows = []
    for sku, (volume, price, cost) in budget.items():
        rows.append(
            {
                "month": "2026-06",
                "branch": "Nairobi CBD",
                "sku": sku,
                "volume": volume,
                "price": price,
                "unit_cost": cost,
            }
        )
    actual_rows = []
    for sku, (volume, price, cost) in actual.items():
        actual_rows.append(
            {
                "month": "2026-06",
                "branch": "Nairobi CBD",
                "sku": sku,
                "volume": volume,
                "price": price,
                "unit_cost": cost,
            }
        )
    return Ledger.from_dict(
        {
            "seed": 1,
            "fingerprint": "0" * 16,
            "months": ["2026-06"],
            "branches": ["Nairobi CBD"],
            "catalogue": catalogue,
            "budgets": rows,
            "actuals": actual_rows,
            "notes": ["synthetic"],
        }
    )


class FlexedBudgetTest(unittest.TestCase):
    def test_flexed_budget_values_actual_volume_at_budget_rates(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (120, "100.00", "70.00"), "B": (80, "100.00", "90.00")},
        )
        flex = variance.flexed_gross_profit(ledger, "2026-06")
        # 120 at A's budget margin of 30, 80 at B's budget margin of 10.
        self.assertEqual(flex, D("4400.00"))

    def test_flexed_budget_ignores_actual_price_and_cost(self):
        cheap = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (100, "80.00", "60.00"), "B": (100, "80.00", "60.00")},
        )
        self.assertEqual(variance.flexed_gross_profit(cheap, "2026-06"), D("4000.00"))

    def test_flexed_minus_budget_equals_volume_plus_mix(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (150, "100.00", "70.00"), "B": (50, "100.00", "90.00")},
        )
        bridge = variance.bridge_for_month(ledger, "2026-06")
        self.assertEqual(
            bridge.flexed_gp - bridge.budget_gp, bridge.volume + bridge.mix
        )

    def test_actual_minus_flexed_equals_price_plus_cost(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (100, "95.00", "72.00"), "B": (100, "95.00", "72.00")},
        )
        bridge = variance.bridge_for_month(ledger, "2026-06")
        self.assertEqual(
            bridge.actual_gp - bridge.flexed_gp, bridge.price + bridge.cost
        )


class BridgeIdentityTest(unittest.TestCase):
    def test_components_sum_exactly_to_the_total_variance(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (130, "96.00", "68.00"), "B": (70, "102.00", "95.00")},
        )
        bridge = variance.bridge_for_month(ledger, "2026-06")
        total = bridge.actual_gp - bridge.budget_gp
        self.assertEqual(
            bridge.volume + bridge.mix + bridge.price + bridge.cost, total
        )

    def test_bridge_closes_exactly_on_the_generated_ledger(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        for month in ("2025-06", "2026-01", "2026-06"):
            bridge = variance.bridge_for_month(ledger, month)
            total = bridge.actual_gp - bridge.budget_gp
            self.assertEqual(
                bridge.volume + bridge.mix + bridge.price + bridge.cost,
                total,
                month,
            )

    def test_every_component_is_money_quantised_to_cents(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        bridge = variance.bridge_for_month(ledger, "2026-06")
        for value in bridge.components.values():
            self.assertIsInstance(value, Decimal)
            self.assertEqual(value, value.quantize(D("0.01")))

    def test_components_are_named_volume_mix_price_and_cost(self):
        ledger = Ledger.from_dict(generator.build_ledger())
        bridge = variance.bridge_for_month(ledger, "2026-06")
        self.assertEqual(
            tuple(bridge.components), ("volume", "mix", "price", "cost")
        )


class ComponentBehaviourTest(unittest.TestCase):
    def test_mix_nets_to_zero_when_every_product_scales_together(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (200, "100.00", "70.00"), "B": (200, "100.00", "90.00")},
        )
        bridge = variance.bridge_for_month(ledger, "2026-06")
        self.assertEqual(bridge.mix, D("0.00"))

    def test_mix_is_adverse_when_volume_shifts_to_the_lower_margin_product(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (50, "100.00", "70.00"), "B": (150, "100.00", "90.00")},
        )
        bridge = variance.bridge_for_month(ledger, "2026-06")
        self.assertEqual(bridge.volume, D("0.00"))
        self.assertEqual(bridge.mix, D("-1000.00"))

    def test_volume_variance_is_total_volume_change_at_budget_margin(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (120, "100.00", "70.00"), "B": (120, "100.00", "90.00")},
        )
        bridge = variance.bridge_for_month(ledger, "2026-06")
        # 40 extra units at the budget gross profit per unit of 20.
        self.assertEqual(bridge.volume, D("800.00"))
        self.assertEqual(bridge.mix, D("0.00"))

    def test_price_variance_is_zero_when_prices_match_the_budget(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (130, "100.00", "70.00"), "B": (70, "100.00", "90.00")},
        )
        self.assertEqual(variance.bridge_for_month(ledger, "2026-06").price, D("0.00"))

    def test_price_variance_is_adverse_when_the_selling_price_falls(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (100, "95.00", "70.00"), "B": (100, "95.00", "90.00")},
        )
        self.assertEqual(variance.bridge_for_month(ledger, "2026-06").price, D("-1000.00"))

    def test_cost_variance_is_favourable_when_the_unit_cost_falls(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (100, "100.00", "65.00"), "B": (100, "100.00", "85.00")},
        )
        self.assertEqual(variance.bridge_for_month(ledger, "2026-06").cost, D("1000.00"))

    def test_cost_variance_is_adverse_when_the_unit_cost_rises(self):
        ledger = micro_ledger(
            {"A": (100, "100.00", "70.00"), "B": (100, "100.00", "90.00")},
            {"A": (100, "100.00", "75.00"), "B": (100, "100.00", "95.00")},
        )
        self.assertEqual(variance.bridge_for_month(ledger, "2026-06").cost, D("-1000.00"))


class MonthAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger.from_dict(generator.build_ledger())
        self.analysis = variance.analyse_month(self.ledger, "2026-06")

    def test_analysis_reports_budget_actual_and_variance(self):
        self.assertEqual(self.analysis.month, "2026-06")
        self.assertGreater(self.analysis.budget_gross_profit, 0)
        self.assertGreater(self.analysis.actual_gross_profit, 0)
        self.assertEqual(
            self.analysis.gross_profit_variance,
            self.analysis.actual_gross_profit - self.analysis.budget_gross_profit,
        )

    def test_analysis_splits_gross_profit_by_branch(self):
        self.assertEqual(len(self.analysis.by_branch), len(BRANCHES))
        total = sum(row.actual_gross_profit for row in self.analysis.by_branch)
        self.assertEqual(total, self.analysis.actual_gross_profit)

    def test_analysis_splits_gross_profit_by_category(self):
        self.assertEqual(len(self.analysis.by_category), 4)
        total = sum(row.actual_gross_profit for row in self.analysis.by_category)
        self.assertEqual(total, self.analysis.actual_gross_profit)

    def test_every_variance_component_belongs_to_one_owner(self):
        owners = variance.owner_totals(self.analysis.bridge)
        self.assertEqual(
            sum(owners.values()), self.analysis.gross_profit_variance
        )
        self.assertEqual(len(owners), 4)

    def test_the_planted_drivers_show_up_with_the_expected_signs(self):
        bridge = self.analysis.bridge
        self.assertLess(bridge.price, 0, "discount creep should hurt price")
        self.assertLess(bridge.cost, 0, "the supplier step should hurt cost")
        self.assertLess(bridge.mix, 0, "the shift into staples should hurt mix")


class ExceptionTest(unittest.TestCase):
    def setUp(self):
        self.ledger = Ledger.from_dict(generator.build_ledger())
        self.analysis = variance.analyse_month(self.ledger, "2026-06")

    def test_exceptions_are_sorted_by_impact_descending(self):
        impacts = [abs(e.gross_profit_impact) for e in self.analysis.exceptions]
        self.assertEqual(impacts, sorted(impacts, reverse=True))

    def test_every_exception_names_an_owner_and_an_action(self):
        self.assertTrue(self.analysis.exceptions)
        for exception in self.analysis.exceptions:
            self.assertTrue(exception.owner)
            self.assertTrue(exception.action)
            self.assertTrue(exception.finding)

    def test_the_discount_creep_is_flagged_as_a_price_exception(self):
        drivers = {e.driver for e in self.analysis.exceptions}
        self.assertIn("price", drivers)
        self.assertIn("cost", drivers)

    def test_materiality_threshold_filters_small_lines(self):
        loose = variance.analyse_month(self.ledger, "2026-06", materiality=D("0"))
        tight = variance.analyse_month(self.ledger, "2026-06", materiality=D("1000000"))
        self.assertGreater(len(loose.exceptions), len(tight.exceptions))


if __name__ == "__main__":
    unittest.main()
