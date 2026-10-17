"""The README quotes numbers, so those numbers are checked against the answer key.

This exists because a hand-typed figure rots silently the moment the ledger or
the bridge changes.
"""

import json
import unittest
from decimal import Decimal
from pathlib import Path

from pack import generator, report
from pack.model import Ledger

ROOT = Path(__file__).resolve().parent.parent
MONTH = "2026-06"


class ReadmeDriftTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.key = report.build_answer_key(cls.ledger, MONTH)
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
        self.assertIn("15/15", self.readme)
        self.assertIn(f"{len(self.key['exceptions'])} exceptions", self.readme)

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
        quoted = {
            token.replace(",", "")
            for token in self.readme.replace("KES ", " ").split()
            if token.replace(",", "").replace(".", "").isdigit() and "." in token
        }
        unknown = {
            token for token in quoted
            if token not in {v.replace(",", "") for v in key_values}
            and Decimal(token) > Decimal("1000")
        }
        self.assertEqual(unknown, set(), f"README figures not in the answer key: {unknown}")


if __name__ == "__main__":
    unittest.main()
