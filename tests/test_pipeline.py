"""End-to-end tests: one command produces every artefact, twice, identically."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from pack import pipeline

MONTH = "2026-06"

EXPECTED = (
    "data/ledger.json",
    "outputs/answer_key.json",
    "outputs/answer_key.md",
    "outputs/MONTHLY_PACK.md",
    "outputs/validation_report.md",
    "outputs/tables/bridge.csv",
    "outputs/tables/exceptions.csv",
    "outputs/tables/branch_variance.csv",
    "outputs/tables/category_variance.csv",
    "outputs/charts/01_bridge_waterfall.png",
    "outputs/charts/02_gross_profit_trend.png",
    "outputs/charts/03_variance_by_owner.png",
)


def _hashes(root: Path):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class PipelineTest(unittest.TestCase):
    def test_run_writes_every_expected_artefact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline.run(month=MONTH, root=root)
            for relative in EXPECTED:
                self.assertTrue((root / relative).exists(), relative)

    def test_second_run_reproduces_every_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pipeline.run(month=MONTH, root=root)
            first = _hashes(root)
            pipeline.run(month=MONTH, root=root)
            second = _hashes(root)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(EXPECTED))

    def test_validation_report_states_fifteen_of_fifteen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary = pipeline.run(month=MONTH, root=root)
            text = (root / "outputs/validation_report.md").read_text()
        self.assertIn("15/15", text)
        self.assertTrue(summary["all_passed"])

    def test_unknown_month_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                pipeline.run(month="2024-01", root=Path(tmp))


if __name__ == "__main__":
    unittest.main()
