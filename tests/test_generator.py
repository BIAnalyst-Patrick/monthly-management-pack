"""Contract tests for the seeded budget-and-actuals ledger.

These are written before the generator exists: the ledger is the foundation
every variance figure rests on, so its shape, its determinism and the four
planted drivers are pinned down first.
"""

import json
import unittest

from pack import generator
from pack.model import (
    BRANCHES,
    CATEGORIES,
    MONTHS,
    SKUS_PER_CATEGORY,
    SEED,
)


class LedgerFixture:
    """Build the default ledger once and share it across tests."""

    _ledger = None

    @classmethod
    def ledger(cls):
        if cls._ledger is None:
            cls._ledger = generator.build_ledger()
        return cls._ledger


def _rows(ledger, kind):
    return ledger[kind]


def _actual_rows(ledger, month, branch=None, category=None):
    out = []
    for row in _rows(ledger, "actuals"):
        if row["month"] != month:
            continue
        if branch is not None and row["branch"] != branch:
            continue
        if category is not None and _category_of(ledger, row["sku"]) != category:
            continue
        out.append(row)
    return out


def _budget_rows(ledger, month, branch=None, category=None):
    out = []
    for row in _rows(ledger, "budgets"):
        if row["month"] != month:
            continue
        if branch is not None and row["branch"] != branch:
            continue
        if category is not None and _category_of(ledger, row["sku"]) != category:
            continue
        out.append(row)
    return out


def _category_of(ledger, sku):
    for item in ledger["catalogue"]:
        if item["sku"] == sku:
            return item["category"]
    raise KeyError(sku)


class LedgerShapeTest(unittest.TestCase):
    def test_ledger_spans_eighteen_months_from_january_2025_to_june_2026(self):
        ledger = LedgerFixture.ledger()
        self.assertEqual(len(ledger["months"]), 18)
        self.assertEqual(ledger["months"][0], "2025-01")
        self.assertEqual(ledger["months"][-1], "2026-06")
        self.assertEqual(tuple(ledger["months"]), MONTHS)

    def test_ledger_covers_three_branches_and_four_categories(self):
        ledger = LedgerFixture.ledger()
        self.assertEqual(tuple(ledger["branches"]), BRANCHES)
        self.assertEqual(len(BRANCHES), 3)
        self.assertEqual(
            sorted({item["category"] for item in ledger["catalogue"]}),
            sorted(CATEGORIES),
        )

    def test_catalogue_holds_forty_skus_ten_per_category(self):
        ledger = LedgerFixture.ledger()
        self.assertEqual(len(ledger["catalogue"]), len(CATEGORIES) * SKUS_PER_CATEGORY)
        for category in CATEGORIES:
            count = sum(1 for i in ledger["catalogue"] if i["category"] == category)
            self.assertEqual(count, SKUS_PER_CATEGORY, category)

    def test_budget_has_one_line_per_month_branch_and_sku(self):
        ledger = LedgerFixture.ledger()
        expected = len(MONTHS) * len(BRANCHES) * len(ledger["catalogue"])
        self.assertEqual(len(_rows(ledger, "budgets")), expected)

    def test_actuals_have_one_line_per_month_branch_and_sku(self):
        ledger = LedgerFixture.ledger()
        expected = len(MONTHS) * len(BRANCHES) * len(ledger["catalogue"])
        self.assertEqual(len(_rows(ledger, "actuals")), expected)


class LedgerDeterminismTest(unittest.TestCase):
    def test_same_seed_reproduces_an_identical_ledger(self):
        first = generator.build_ledger()
        second = generator.build_ledger()
        self.assertEqual(
            json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True)
        )

    def test_fingerprint_is_sixteen_hex_characters(self):
        fingerprint = LedgerFixture.ledger()["fingerprint"]
        self.assertEqual(len(fingerprint), 16)
        int(fingerprint, 16)

    def test_fingerprint_changes_when_the_seed_changes(self):
        other = generator.build_ledger(seed=SEED + 1)
        self.assertNotEqual(other["fingerprint"], LedgerFixture.ledger()["fingerprint"])

    def test_fingerprint_is_not_part_of_its_own_hash(self):
        ledger = LedgerFixture.ledger()
        payload = {k: v for k, v in ledger.items() if k != "fingerprint"}
        self.assertEqual(ledger["fingerprint"], generator.fingerprint_of(payload))


class LedgerPlantedDriversTest(unittest.TestCase):
    """The four mechanisms the diagnosis is supposed to find."""

    def test_discount_creep_shows_in_nakuru_beverages_prices(self):
        ledger = LedgerFixture.ledger()
        first = _actual_rows(ledger, MONTHS[0], "Nakuru", "Beverages")
        last = _actual_rows(ledger, MONTHS[-1], "Nakuru", "Beverages")
        budget_last = _budget_rows(ledger, MONTHS[-1], "Nakuru", "Beverages")

        start = sum(float(r["price"]) for r in first) / len(first)
        budget_start = sum(
            float(r["price"]) for r in _budget_rows(ledger, MONTHS[0], "Nakuru", "Beverages")
        ) / len(first)
        end = sum(float(r["price"]) for r in last) / len(last)
        budget_end = sum(float(r["price"]) for r in budget_last) / len(budget_last)

        self.assertLess(end / budget_end, 0.95, "expected a visible discount by month 18")
        self.assertLess(end / budget_end, start / budget_start - 0.05)

    def test_supplier_cost_step_raises_home_care_cost_from_month_thirteen(self):
        ledger = LedgerFixture.ledger()
        before = _actual_rows(ledger, "2025-12", "Nairobi CBD", "Home Care")
        after = _actual_rows(ledger, "2026-06", "Nairobi CBD", "Home Care")
        budget_before = _budget_rows(ledger, "2025-12", "Nairobi CBD", "Home Care")
        budget_after = _budget_rows(ledger, "2026-06", "Nairobi CBD", "Home Care")

        def cost_index(actual, budget):
            actual_cost = sum(float(a["unit_cost"]) * a["volume"] for a in actual)
            budget_cost = sum(float(b["unit_cost"]) * a["volume"] for a, b in zip(actual, budget))
            return actual_cost / budget_cost

        self.assertLess(cost_index(before, budget_before), 1.02)
        self.assertGreater(cost_index(after, budget_after), 1.04)

    def test_mombasa_road_volume_trails_the_other_branches(self):
        ledger = LedgerFixture.ledger()

        def growth(branch):
            early = sum(r["volume"] for r in _actual_rows(ledger, MONTHS[2], branch))
            late = sum(r["volume"] for r in _actual_rows(ledger, MONTHS[-1], branch))
            return late / early

        mombasa = growth("Mombasa Road")
        nairobi = growth("Nairobi CBD")
        self.assertLess(mombasa, nairobi - 0.05)

    def test_staples_take_a_larger_share_of_volume_by_the_end(self):
        ledger = LedgerFixture.ledger()

        def share(month):
            rows = _actual_rows(ledger, month)
            total = sum(r["volume"] for r in rows)
            staples = sum(
                r["volume"] for r in rows
                if _category_of(ledger, r["sku"]) == "Staples"
            )
            return staples / total

        self.assertGreater(share(MONTHS[-1]), share(MONTHS[2]) + 0.03)


class LedgerArithmeticTest(unittest.TestCase):
    def test_every_line_has_positive_volume_price_and_cost(self):
        ledger = LedgerFixture.ledger()
        for kind in ("budgets", "actuals"):
            for row in _rows(ledger, kind):
                self.assertGreater(row["volume"], 0)
                self.assertGreater(float(row["price"]), 0)
                self.assertGreater(float(row["unit_cost"]), 0)

    def test_cost_stays_below_price_on_every_line(self):
        ledger = LedgerFixture.ledger()
        for kind in ("budgets", "actuals"):
            for row in _rows(ledger, kind):
                self.assertLess(float(row["unit_cost"]), float(row["price"]))

    def test_budget_price_is_constant_within_a_year_per_sku(self):
        ledger = LedgerFixture.ledger()
        seen = {}
        for row in _rows(ledger, "budgets"):
            key = (row["month"][:4], row["sku"])
            price = row["price"]
            if key in seen:
                self.assertEqual(seen[key], price, key)
            else:
                seen[key] = price

    def test_ledger_declares_its_own_synthetic_origin(self):
        ledger = LedgerFixture.ledger()
        self.assertEqual(ledger["seed"], SEED)
        self.assertTrue(any("synthetic" in note.lower() for note in ledger["notes"]))


if __name__ == "__main__":
    unittest.main()
