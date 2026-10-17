"""Money and percentage formatting: one module, one contract per shape.

Four helpers used to disagree across the package, so a caller could silently get
a Decimal where it expected a grouped string. Each shape now has exactly one
name, and its output is pinned by ``tests/test_money.py``:

| function  | returns                      | example            | used for            |
|-----------|------------------------------|--------------------|---------------------|
| ``cents`` | Decimal, 2dp, half-up         | ``Decimal("-0.01")`` | arithmetic        |
| ``plain`` | str, no separators, 2dp      | ``"-41943.76"``    | JSON, CSV           |
| ``grouped``| str, thousands, 2dp         | ``"-41,943.76"``   | markdown tables     |
| ``kes``   | str, ``KES `` + grouped      | ``"KES 41,943.76"``| prose               |
| ``pct``   | str, 2dp, no ``%``           | ``"-19.38"``       | JSON, markdown      |
| ``compact``| str, abbreviated             | ``"-42K"``         | chart labels        |
"""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def cents(value) -> Decimal:
    """Quantise to cents, half-up, as an invoice would round."""
    return _decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def plain(value) -> str:
    """Wire format: no thousands separators, always two decimal places."""
    return str(cents(value))


def grouped(value) -> str:
    """Human table format: thousands separators, two decimal places."""
    return f"{cents(value):,.2f}"


def kes(value, *, absolute: bool = False) -> str:
    """Prose format. ``absolute`` is for quoting a charge as a positive cost."""
    amount = abs(cents(value)) if absolute else cents(value)
    return f"KES {amount:,.2f}"


def pct(value) -> str:
    """Percentage to two decimal places, no ``%`` suffix, e.g. ``-19.38``."""
    return f"{cents(value):.2f}"


def compact(value) -> str:
    """Abbreviated label for a chart axis: ``42K``, ``1.46M``, ``0``."""
    amount = _decimal(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    if amount >= 1_000_000:
        return f"{sign}{amount / 1_000_000:,.2f}M"
    if amount >= 1_000:
        return f"{sign}{amount / 1_000:,.0f}K"
    return f"{sign}{amount:,.0f}"
