"""The README quotes numbers, so those numbers are checked against the answer key.

This exists because a hand-typed figure rots silently the moment the ledger or
the bridge changes.
"""

import json
import unittest
from decimal import Decimal
from pathlib import Path

from pack import generator, key
from pack.model import Ledger

ROOT = Path(__file__).resolve().parent.parent
MONTH = "2026-06"


class ReadmeDriftTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.key = key.build_answer_key(cls.ledger, MONTH)
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def money(self, value) -> str:
        return f"{Decimal(value):,.2f}"

    def test_readme_quotes_the_bridge_exactly(self):
        for component in ("volume", "mix", "price", "cost", "total"):
            published = self.money(self.key["bridge"][component])
            self.assertIn(published, self.readme, component)

    def test_readme_quotes_the_headline_variance(self):
        variance = self.money(self.key["headline"]["gross_profit_variance"])
        percent = self.key["headline"]["gross_profit_variance_pct"]
        self.assertIn(variance, self.readme)
        self.assertIn(percent, self.readme)

    def test_readme_quotes_the_ledger_fingerprint(self):
        self.assertIn(self.key["fingerprint"], self.readme)

    def test_readme_states_the_validation_and_exception_counts(self):
        self.assertIn("17/17", self.readme)
        self.assertIn(f"{len(self.key['exceptions'])} exceptions", self.readme)

    def test_readme_quotes_the_line_table_it_publishes(self):
        self.assertIn("line_variance.csv", self.readme)
        for row in self.key["lines"][:5]:
            self.assertIn(f"{Decimal(row['variance']):,.2f}", self.readme)

    def test_readme_declares_the_data_synthetic_before_the_fold(self):
        head = "\n".join(self.readme.splitlines()[:40]).lower()
        self.assertIn("synthetic", head)

    def test_readme_numbers_are_all_derived_from_the_answer_key(self):
        published = set()

        def collect(node):
            if isinstance(node, dict):
                for value in node.values():
                    collect(value)
            elif isinstance(node, list):
                for value in node:
                    collect(value)
            elif isinstance(node, str):
                bare = node.replace("-", "")
                if bare.replace(".", "").isdigit() and "." in node:
                    published.add(f"{Decimal(node):,.2f}")

        collect(self.key)
        key_values = published
        quoted = set()
        for token in self.readme.replace("KES ", " ").split():
            # Normalise the typographic minus so negative figures are guarded too.
            cleaned = token.replace("\u2212", "-").replace(",", "")
            bare = cleaned.lstrip("-")
            if bare.replace(".", "").isdigit() and "." in bare:
                quoted.add(cleaned)
        unknown = {
            token for token in quoted
            if token not in {v.replace(",", "") for v in key_values}
            and abs(Decimal(token)) > Decimal("1000")
        }
        self.assertEqual(unknown, set(), f"README figures not in the answer key: {unknown}")


class ActionPlanTest(unittest.TestCase):
    """The Monday action plan is what a manager acts on, so it is guarded where
    it sits: in the first screen, after the charts, with an owner from the
    answer key on every action.
    """

    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.key = key.build_answer_key(cls.ledger, MONTH)
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")

    def section(self):
        _, found, rest = self.readme.partition("## What happens Monday")
        self.assertTrue(found, "README has no 'What happens Monday' action plan")
        return rest.split("\n## ", 1)[0]

    def table(self):
        rows = [
            line for line in self.section().splitlines()
            if line.strip().startswith("|")
        ]
        return [[cell.strip() for cell in row.strip("|").split("|")] for row in rows]

    def test_the_action_plan_sits_in_the_first_screen_after_the_charts(self):
        self.assertIn("## What happens Monday", self.readme)
        self.assertLess(
            self.readme.index("## What it looks like"),
            self.readme.index("## What happens Monday"),
            "the action plan must come after the charts",
        )
        self.assertLess(
            self.readme.index("## What happens Monday"),
            self.readme.index("## The deliverables"),
            "the action plan must come before the deliverables",
        )

    def test_every_action_in_the_plan_carries_an_owner_from_the_answer_key(self):
        table = self.table()
        self.assertTrue(table, "the action plan needs a table of actions")
        self.assertIn("Owner", table[0], "the action plan table needs an Owner column")
        owner = table[0].index("Owner")
        actions = table[2:]  # header and separator rows
        self.assertEqual(len(actions), 3, "the plan is three actions")
        for row in actions:
            self.assertIn(
                row[owner], self.key["owners"],
                f"action without an owner from the answer key: {row}",
            )


if __name__ == "__main__":
    unittest.main()
