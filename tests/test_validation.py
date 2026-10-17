"""Tests for the published validation report.

A check that cannot fail proves nothing, so one test tampers with the answer
key and expects the drift guard to catch it.
"""

import copy
import unittest

from pack import generator, report, validation, variance
from pack.model import Ledger

MONTH = "2026-06"


class ValidationFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.analysis = variance.analyse_month(cls.ledger, MONTH)
        cls.key = report.build_answer_key(cls.ledger, MONTH)


class CheckSuiteTest(ValidationFixture):
    def test_seventeen_checks_are_published(self):
        checks = validation.run_checks(self.ledger, self.analysis, self.key)
        self.assertEqual(len(checks), 17)

    def test_the_two_checks_the_plan_named_are_present(self):
        names = {c.name for c in validation.run_checks(self.ledger, self.analysis, self.key)}
        self.assertIn("exception list is sorted by impact", names)
        self.assertIn("unit-cost drift sums to the bridge cost", names)

    def test_the_line_table_is_reconciled_to_the_bridge(self):
        names = {c.name for c in validation.run_checks(self.ledger, self.analysis, self.key)}
        self.assertIn("line variances sum to the bridge total", names)

    def test_every_check_passes_on_an_honest_answer_key(self):
        checks = validation.run_checks(self.ledger, self.analysis, self.key)
        failed = [c for c in checks if not c.passed]
        self.assertEqual(failed, [], [f"{c.name}: {c.detail}" for c in failed])

    def test_check_names_are_unique_and_described(self):
        checks = validation.run_checks(self.ledger, self.analysis, self.key)
        names = [c.name for c in checks]
        self.assertEqual(len(names), len(set(names)))
        for check in checks:
            self.assertTrue(check.name)
            self.assertTrue(check.detail)


class DriftGuardTest(ValidationFixture):
    def test_tampering_with_a_bridge_component_is_caught(self):
        tampered = copy.deepcopy(self.key)
        tampered["bridge"]["price"] = "1.00"
        checks = validation.run_checks(self.ledger, self.analysis, tampered)
        self.assertFalse(validation.all_passed(checks))
        failed_names = {c.name for c in checks if not c.passed}
        self.assertIn("answer key matches recomputed bridge", failed_names)

    def test_tampering_with_the_headline_variance_is_caught(self):
        tampered = copy.deepcopy(self.key)
        tampered["headline"]["gross_profit_variance"] = "0.00"
        checks = validation.run_checks(self.ledger, self.analysis, tampered)
        self.assertFalse(validation.all_passed(checks))

    def test_a_hand_edited_ledger_is_caught_by_its_fingerprint(self):
        broken = copy.deepcopy(generator.build_ledger())
        broken["actuals"][0]["price"] = "999999.00"
        ledger = Ledger.from_dict(broken)
        analysis = variance.analyse_month(ledger, MONTH)
        key = report.build_answer_key(ledger, MONTH)
        checks = validation.run_checks(ledger, analysis, key)
        failed_names = {c.name for c in checks if not c.passed}
        self.assertIn("fingerprint matches the canonical ledger", failed_names)


class ValidationReportMarkdownTest(ValidationFixture):
    def test_report_lists_every_check_with_its_outcome(self):
        checks = validation.run_checks(self.ledger, self.analysis, self.key)
        text = validation.render_report(checks)
        for check in checks:
            self.assertIn(check.name, text)
        self.assertIn("17/17", text)

    def test_report_counts_identities_rather_than_claiming_independence(self):
        checks = validation.run_checks(self.ledger, self.analysis, self.key)
        text = validation.render_report(checks)
        self.assertIn("distinct identities", text)
        self.assertNotIn("independent checks", text)


if __name__ == "__main__":
    unittest.main()
