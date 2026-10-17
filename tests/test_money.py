"""One formatter, one contract per shape.

The old code had four helpers that disagreed: some returned a Decimal, some a
string, some grouped thousands, one abbreviated to K/M. These tests pin exactly
what each named shape produces so a caller cannot pick the wrong one by accident.
"""

import pathlib
import unittest
from decimal import Decimal

from pack import money

D = Decimal


class CentsTest(unittest.TestCase):
    def test_cents_quantises_to_two_places(self):
        self.assertEqual(money.cents(D("1463426.7")), D("1463426.70"))
        self.assertEqual(money.cents("12.345"), D("12.35"))
        self.assertEqual(money.cents(D("-0.005")), D("-0.01"))

    def test_cents_returns_a_decimal(self):
        self.assertIsInstance(money.cents(1), Decimal)


class PlainTest(unittest.TestCase):
    def test_plain_has_no_thousands_separator(self):
        self.assertEqual(money.plain(D("1463426.72")), "1463426.72")

    def test_plain_keeps_two_decimal_places(self):
        self.assertEqual(money.plain(D("0")), "0.00")
        self.assertEqual(money.plain(D("-41")), "-41.00")


class GroupedTest(unittest.TestCase):
    def test_grouped_inserts_thousands_separators(self):
        self.assertEqual(money.grouped(D("1463426.72")), "1,463,426.72")

    def test_grouped_keeps_the_sign(self):
        self.assertEqual(money.grouped(D("-41943.76")), "-41,943.76")


class KesTest(unittest.TestCase):
    def test_kes_prefixes_the_grouped_amount(self):
        self.assertEqual(money.kes(D("8755.42")), "KES 8,755.42")

    def test_kes_can_report_an_absolute_charge(self):
        self.assertEqual(money.kes(D("-41382.41"), absolute=True), "KES 41,382.41")


class PctTest(unittest.TestCase):
    def test_pct_is_two_places_without_a_percent_suffix(self):
        self.assertEqual(money.pct(D("-19.3812")), "-19.38")
        self.assertEqual(money.pct(D("0")), "0.00")


class CompactTest(unittest.TestCase):
    def test_compact_abbreviates_thousands_and_millions(self):
        self.assertEqual(money.compact(D("-41943.76")), "-42K")
        self.assertEqual(money.compact(D("1463426.72")), "1.46M")
        self.assertEqual(money.compact(D("0")), "0")


class SingleFormatterTest(unittest.TestCase):
    def test_pack_does_not_define_its_own_formatters(self):
        root = pathlib.Path(__file__).resolve().parent.parent / "pack"

        offenders = []
        for path in root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            for name in ("def _money", "def _thousands", "def _pct", "def _format_money"):
                if name in source:
                    offenders.append(f"{path.name}:{name}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
