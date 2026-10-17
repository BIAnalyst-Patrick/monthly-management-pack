"""A second month, committed, so the renderers run on data they were not written for.

The published pack is June 2026, which always carries four exceptions and so
always fills the "what I would do first" list to three items. December 2025 has
one exception, so it exercises the short-list branch and a different set of
figures. These fixtures are golden files: regenerate them deliberately with
``make fixture`` when the renderers change, never by hand.
"""

import json
import tempfile
import unittest
from pathlib import Path

from pack import generator, key, pipeline, render
from pack.analysis import analyse_month
from pack.model import Ledger

MONTH = "2025-12"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / MONTH
FILES = ("answer_key.json", "answer_key.md", "MONTHLY_PACK.md")


class FixtureMonthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.analysis = analyse_month(cls.ledger, MONTH)
        cls.key = key.build_answer_key(cls.ledger, MONTH)

    def test_the_fixture_month_is_not_the_published_month(self):
        self.assertNotEqual(MONTH, pipeline.DEFAULT_MONTH)
        self.assertEqual(self.key["month"], MONTH)
        self.assertEqual(self.analysis.month, MONTH)

    def test_every_fixture_file_is_present(self):
        for name in FILES:
            self.assertTrue((FIXTURES / name).is_file(), name)

    def test_the_generated_answer_key_matches_the_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = key.write_json(self.key, Path(tmp) / "answer_key.json")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                (FIXTURES / "answer_key.json").read_text(encoding="utf-8"),
            )

    def test_the_generated_answer_key_markdown_matches_the_fixture(self):
        self.assertEqual(
            render.answer_key_md(self.key),
            (FIXTURES / "answer_key.md").read_text(encoding="utf-8"),
        )

    def test_the_generated_pack_matches_the_fixture(self):
        self.assertEqual(
            render.monthly_pack(self.analysis, self.key),
            (FIXTURES / "MONTHLY_PACK.md").read_text(encoding="utf-8"),
        )

    def test_the_fixture_reaches_the_short_exception_list(self):
        """One exception, where the published month always has four."""
        self.assertEqual(len(self.key["exceptions"]), 1)
        text = (FIXTURES / "MONTHLY_PACK.md").read_text(encoding="utf-8")
        section = text.split("## What I would do first", 1)[1]
        section = section.split("## Method and limits", 1)[0]
        numbered = [line for line in section.splitlines() if line[:3] in ("1. ", "2. ", "3. ")]
        self.assertEqual(len(numbered), 1)
        self.assertNotIn("2. ", section)

    def test_the_fixture_contains_no_unrendered_values(self):
        for name in ("MONTHLY_PACK.md", "answer_key.md"):
            text = (FIXTURES / name).read_text(encoding="utf-8")
            self.assertNotIn("{", text, name)
            self.assertNotIn("None", text, name)
            self.assertNotIn("NaN", text, name)

    def test_the_fixture_key_is_valid_json_with_the_expected_shape(self):
        published = json.loads((FIXTURES / "answer_key.json").read_text(encoding="utf-8"))
        self.assertEqual(published["month"], MONTH)
        self.assertEqual(len(published["lines"]), 120)
        self.assertEqual(len(published["branch_trends"]), 3)
        self.assertEqual(published["exceptions"], self.key["exceptions"])


if __name__ == "__main__":
    unittest.main()
