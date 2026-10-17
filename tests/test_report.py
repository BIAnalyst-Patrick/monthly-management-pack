"""Tests for the published artefacts: answer key, pack and tables.

The README quotes numbers, so the answer key has to be the single source of
truth for them, and the pack has to be regenerable rather than written by hand.
"""

import csv
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pack import generator, key, render, tables, variance
from pack.model import Ledger

MONTH = "2026-06"


class ReportFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.analysis = variance.analyse_month(cls.ledger, MONTH)
        cls.key = key.build_answer_key(cls.ledger, MONTH)

    def money(self, value):
        return Decimal(value)


class AnswerKeyTest(ReportFixture):
    def test_key_names_the_month_and_the_ledger_fingerprint(self):
        self.assertEqual(self.key["month"], MONTH)
        self.assertEqual(self.key["fingerprint"], self.ledger.fingerprint)

    def test_key_carries_the_headline_figures(self):
        headline = self.key["headline"]
        for field in (
            "revenue_budget",
            "revenue_actual",
            "revenue_variance_pct",
            "gross_profit_budget",
            "gross_profit_actual",
            "gross_profit_variance",
            "gross_profit_variance_pct",
            "largest_driver",
        ):
            self.assertIn(field, headline)
        self.assertEqual(
            self.money(headline["gross_profit_variance"]),
            self.analysis.gross_profit_variance,
        )

    def test_key_bridge_components_sum_to_the_published_total(self):
        bridge = self.key["bridge"]
        total = sum(self.money(bridge[name]) for name in ("volume", "mix", "price", "cost"))
        self.assertEqual(total, self.money(bridge["total"]))

    def test_key_states_money_as_two_decimal_strings(self):
        for name in ("volume", "mix", "price", "cost", "total"):
            value = self.key["bridge"][name]
            self.assertIsInstance(value, str, name)
            self.assertEqual(value, str(Decimal(value).quantize(Decimal("0.01"))))

    def test_key_lists_the_exceptions_with_an_owner_and_an_action(self):
        self.assertTrue(self.key["exceptions"])
        for row in self.key["exceptions"]:
            self.assertTrue(row["finding"])
            self.assertTrue(row["owner"])
            self.assertTrue(row["action"])
            self.assertIn(row["driver"], ("volume", "mix", "price", "cost"))

    def test_key_groups_the_variance_by_branch_and_category(self):
        self.assertEqual(len(self.key["by_branch"]), 3)
        self.assertEqual(len(self.key["by_category"]), 4)
        total = sum(Decimal(r["variance"]) for r in self.key["by_branch"])
        self.assertEqual(total, self.analysis.gross_profit_variance)

    def test_key_records_the_owner_totals(self):
        owners = self.key["owners"]
        self.assertEqual(len(owners), 4)
        self.assertEqual(
            sum(Decimal(v) for v in owners.values()),
            self.analysis.gross_profit_variance,
        )

    def test_key_publishes_every_line_with_an_owner(self):
        lines = self.key["lines"]
        self.assertEqual(len(lines), 120)
        for row in lines:
            self.assertTrue(row["owner"])
            self.assertEqual(
                Decimal(row["price"])
                + Decimal(row["cost_rate"])
                + Decimal(row["volume_revenue"])
                + Decimal(row["volume_cost"]),
                Decimal(row["variance"]),
            )

    def test_key_publishes_the_branch_trends(self):
        trends = {row["branch"]: row for row in self.key["branch_trends"]}
        self.assertEqual(len(trends), 3)
        self.assertTrue(trends["Mombasa Road"]["off_track"])
        self.assertFalse(trends["Nairobi CBD"]["off_track"])


class PackMarkdownTest(ReportFixture):
    def setUp(self):
        self.text = render.monthly_pack(self.analysis, self.key)

    def test_pack_opens_with_the_month_and_the_headline_variance(self):
        self.assertIn(MONTH, self.text.splitlines()[0])
        published = abs(Decimal(self.key["headline"]["gross_profit_variance_pct"]))
        self.assertIn(f"{published:.2f}", self.text)

    def test_pack_names_all_four_bridge_components(self):
        lowered = self.text.lower()
        for component in ("volume", "mix", "price", "cost"):
            self.assertIn(component, lowered)

    def test_pack_lists_every_exception_with_its_owner(self):
        for exception in self.analysis.exceptions:
            self.assertIn(exception.label, self.text)
            self.assertIn(exception.owner, self.text)

    def test_pack_states_that_the_data_is_synthetic(self):
        self.assertIn("synthetic", self.text.lower())

    def test_pack_lists_the_worst_lines_with_their_owners(self):
        worst = self.key["lines"][0]
        self.assertIn(worst["product"], self.text)
        self.assertIn(worst["owner"], self.text)
        self.assertIn("by line", self.text.lower())

    def test_pack_reports_the_reconciliation_identity(self):
        self.assertIn("reconcil", self.text.lower())


class TablesTest(ReportFixture):
    def test_tables_are_written_as_csv_with_headers(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = tables.write_tables(self.ledger, self.analysis, Path(tmp))
            self.assertEqual(len(paths), 6)
            names = {p.name for p in paths}
            self.assertIn("line_variance.csv", names)
            for path in paths:
                with path.open(newline="") as handle:
                    rows = list(csv.reader(handle))
                self.assertGreater(len(rows), 1, path.name)
                self.assertTrue(rows[0])


if __name__ == "__main__":
    unittest.main()
