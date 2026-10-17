"""The waterfall must actually be a waterfall.

Bars are read back out of the rendered PNG and checked for the property that
defines the chart: each bar starts where the previous one ended, and the chain
starts at budget gross profit. A bar anchored at zero draws a plausible-looking
picture of the wrong thing.
"""

import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image

    HAVE_PIL = True
except ImportError:  # pragma: no cover - charts are optional
    HAVE_PIL = False

from pack import generator, variance
from pack.model import Ledger

ACCENT = (11, 94, 132)
GOOD = (21, 128, 92)
WARN = (176, 58, 46)

WIDTH, HEIGHT = 1240, 700
LEFT, RIGHT, TOP, BOTTOM = 90, WIDTH - 90, 170, HEIGHT - 90


def _longest_run(column, colour):
    best, start = (0, -1), None
    for index, value in enumerate(column):
        if value == colour:
            start = index if start is None else start
        elif start is not None:
            if index - 1 - start > best[1] - best[0]:
                best = (start, index - 1)
            start = None
    if start is not None and len(column) - 1 - start > best[1] - best[0]:
        best = (start, len(column) - 1)
    return best


@unittest.skipUnless(HAVE_PIL, "chart checks need Pillow")
class WaterfallGeometryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pack import charts

        cls.ledger = Ledger.from_dict(generator.build_ledger())
        cls.analysis = variance.analyse_month(cls.ledger, "2026-06")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bridge.png"
            charts.bridge_waterfall(cls.analysis, path)
            image = Image.open(path).convert("RGB")
        cls.pixels = image.load()

    def bar(self, index):
        """(top, bottom, colour) of the bar drawn for step ``index``."""
        slot = (RIGHT - LEFT) / 6
        cx = int(LEFT + slot * index + slot / 2)
        top_of_scan = TOP - 40
        column = [self.pixels[cx, y] for y in range(top_of_scan, BOTTOM + 4)]
        for colour in (ACCENT, GOOD, WARN):
            start, end = _longest_run(column, colour)
            if end - start >= 2:
                return start + top_of_scan, end + top_of_scan, colour
        self.fail(f"no bar of at least three rows at column {cx} for step {index}")

    def test_the_chain_starts_at_the_budget_bar(self):
        budget_top, _, budget_colour = self.bar(0)
        self.assertEqual(budget_colour, ACCENT)
        _, first_bottom, first_colour = self.bar(1)
        self.assertEqual(first_colour, GOOD, "volume is favourable in this month")
        self.assertLessEqual(abs(first_bottom - budget_top), 2)

    def test_each_bar_starts_where_the_previous_one_ended(self):
        for index in (2, 3, 4):
            _, prev_bottom, prev_colour = self.bar(index - 1)
            prev_top, _, _ = self.bar(index - 1)
            previous_end = prev_top if prev_colour == GOOD else prev_bottom
            top, bottom, colour = self.bar(index)
            own_start = bottom if colour == GOOD else top
            self.assertLessEqual(
                abs(own_start - previous_end), 2,
                f"step {index} starts at {own_start}, previous bar ends at {previous_end}",
            )

    def test_the_chain_lands_on_the_actual_gross_profit_bar(self):
        _, cost_bottom, cost_colour = self.bar(4)
        cost_top, _, _ = self.bar(4)
        cost_end = cost_top if cost_colour == GOOD else cost_bottom
        actual_top, _, actual_colour = self.bar(5)
        self.assertEqual(actual_colour, ACCENT)
        self.assertLessEqual(abs(actual_top - cost_end), 2)


if __name__ == "__main__":
    unittest.main()
