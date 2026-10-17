"""The published documents must say what the pack says.

The report and the brief are generated, so they are compared byte for byte with a
fresh build. The PDF and the deck are checked for the structure a reader relies
on: page and slide counts, the month, the owner names and the action values. The
binary checks need the optional docs extras and skip without them.
"""

import contextlib
import importlib.util
import io
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from pack import generator, key
from pack.model import Ledger

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MONTH = "2026-06"
FILES = (
    f"report-{MONTH}.md",
    "how-a-management-pack-is-produced.md",
    f"monthly-pack-{MONTH}.pdf",
    f"monthly-pack-{MONTH}.pptx",
)

HAVE_PPTX = importlib.util.find_spec("pptx") is not None
HAVE_PDF = importlib.util.find_spec("pypdf") is not None and (
    importlib.util.find_spec("reportlab") is not None
)


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_docs", ROOT / "scripts" / "build_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReportMarkdownTest(unittest.TestCase):
    """Runs without the optional extras: the markdown is the contract."""

    @classmethod
    def setUpClass(cls):
        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.key = key.build_answer_key(cls.ledger, MONTH)
        cls.report = (DOCS / f"report-{MONTH}.md").read_text(encoding="utf-8")
        cls.brief = (DOCS / "how-a-management-pack-is-produced.md").read_text(
            encoding="utf-8"
        )

    def test_the_report_quotes_the_bridge_and_the_headline(self):
        for component in ("volume", "mix", "price", "cost", "total"):
            figure = f"{Decimal(self.key['bridge'][component]):,.2f}"
            self.assertIn(figure, self.report, component)
        self.assertIn(
            f"{abs(Decimal(self.key['headline']['gross_profit_variance_pct']))}%",
            self.report,
        )

    def test_the_report_embeds_every_chart(self):
        for chart in (
            "01_bridge_waterfall.png",
            "02_gross_profit_trend.png",
            "03_variance_by_owner.png",
        ):
            self.assertIn(f"../outputs/charts/{chart}", self.report)

    def test_every_exception_action_appears_with_its_owner(self):
        for row in self.key["exceptions"]:
            self.assertIn(row["owner"], self.report)
            self.assertIn(row["action"], self.report)

    def test_the_brief_states_the_thresholds_it_uses(self):
        for phrase in (
            money(self.key["materiality"]),
            "97.5%",
            "102.5%",
            "2 of the last 3 months",
            "5%",
        ):
            self.assertIn(phrase, self.brief, phrase)

    def test_the_brief_explains_the_real_world_cycle(self):
        for phrase in (
            "close and lock the data",
            "flex the budget",
            "assign an owner",
            "the meeting",
            "what this repository automates",
        ):
            self.assertIn(phrase.lower(), self.brief.lower(), phrase)


def money(value) -> str:
    return f"{Decimal(value):,.2f}"


@unittest.skipUnless(HAVE_PPTX, "the deck check needs python-pptx")
class DeckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pptx import Presentation

        cls.deck = Presentation(str(DOCS / f"monthly-pack-{MONTH}.pptx"))

    def test_the_deck_has_eight_slides_and_names_the_month(self):
        self.assertEqual(len(self.deck.slides), 8)
        cover = " ".join(
            shape.text_frame.text for shape in self.deck.slides[0].shapes
            if shape.has_text_frame
        )
        self.assertIn(MONTH, cover)

    def test_slide_titles_follow_the_reading_order(self):
        titles = []
        for slide in self.deck.slides:
            texts = [
                shape.text_frame.text.splitlines()[0]
                for shape in slide.shapes
                if shape.has_text_frame and shape.text_frame.text.strip()
            ]
            titles.append(texts[0] if texts else "")
        self.assertEqual(
            titles[1:],
            [
                "The headline",
                "Where the profit went",
                "Price and cost did the damage",
                "Who owns it",
                "Line level",
                "What I would do first",
                "Method, limits, and how to regenerate",
            ],
        )

    def test_the_deck_carries_the_two_lead_charts(self):
        kinds = [shape.shape_type for slide in self.deck.slides for shape in slide.shapes]
        pictures = sum(1 for kind in kinds if "PICTURE" in str(kind))
        self.assertGreaterEqual(pictures, 2)


@unittest.skipUnless(HAVE_PDF, "the PDF check needs reportlab and pypdf")
class PdfTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pypdf import PdfReader

        cls.reader = PdfReader(str(DOCS / f"monthly-pack-{MONTH}.pdf"))
        cls.text = "\n".join(page.extract_text() or "" for page in cls.reader.pages)

    def test_the_pdf_is_a_management_pack_not_a_leaflet(self):
        self.assertGreaterEqual(len(self.reader.pages), 6)

    def test_the_pdf_states_the_month_the_fingerprint_and_the_gap(self):
        self.assertIn(MONTH, self.text)
        ledger = Ledger.from_dict(generator.build_ledger())
        self.assertIn(ledger.fingerprint, self.text)
        answer = key.build_answer_key(ledger, MONTH)
        self.assertIn(money(answer["bridge"]["total"]), self.text)

    def test_the_pdf_carries_the_actions_and_their_owners(self):
        answer = key.build_answer_key(Ledger.from_dict(generator.build_ledger()), MONTH)
        for row in answer["exceptions"]:
            self.assertIn(row["owner"], self.text)
            self.assertIn(money(abs(Decimal(row["gross_profit_impact"]))), self.text)


@unittest.skipUnless(HAVE_PPTX and HAVE_PDF, "rebuilding needs the docs extras")
class DocsMatchBuildTest(unittest.TestCase):
    def test_the_committed_documents_match_a_fresh_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stdout(io.StringIO()):
                code = _builder().main(["--out", tmp])
            self.assertEqual(code, 0)
            for name in FILES:
                built = (Path(tmp) / name).read_bytes()
                committed = (DOCS / name).read_bytes()
                self.assertEqual(built, committed, name)


if __name__ == "__main__":
    unittest.main()
