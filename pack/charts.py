"""Report charts, rendered to repo-local PNG files.

Charts are illustrative; every number they show comes from the same analysis the
answer key is built from, and every bar or point carries its own label so the
picture can be read without the table beside it. They are drawn with Pillow so
the output is a plain file in the repository, never a hosted embed.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import bridge as bridge_mod
from . import money
from .analysis import MonthAnalysis

WIDTH, HEIGHT = 1240, 700
BG = (255, 255, 255)
INK = (23, 32, 42)
MUTED = (110, 124, 140)
GRID = (226, 232, 240)
ACCENT = (11, 94, 132)
ACCENT_SOFT = (150, 196, 214)
WARN = (176, 58, 46)
GOOD = (21, 128, 92)

_FONTS = {}


def _font(size: int):
    if size not in _FONTS:
        try:
            _FONTS[size] = ImageFont.load_default(size=size)
        except TypeError:  # older Pillow
            _FONTS[size] = ImageFont.load_default()
    return _FONTS[size]


def _canvas(title: str, subtitle: str):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    draw.text((70, 40), title, font=_font(30), fill=INK)
    draw.text((70, 82), subtitle, font=_font(16), fill=MUTED)
    return img, draw


def _centred(draw, x: float, y: float, text: str, font, fill) -> None:
    width = draw.textlength(text, font=font)
    draw.text((x - width / 2, y), text, font=font, fill=fill)


def _right_aligned(draw, x: float, y: float, text: str, font, fill) -> None:
    width = draw.textlength(text, font=font)
    draw.text((x - width, y), text, font=font, fill=fill)


def _save(img, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)
    return path


def _signed(value) -> str:
    amount = money.compact(value)
    return f"+{amount}" if value >= 0 else amount


def _shortfall_story(analysis: MonthAnalysis) -> str:
    """One sentence naming the driver a reader should look at first."""
    bridge = analysis.bridge
    gap = bridge.total_variance
    components = {
        "volume": bridge.volume,
        "mix": bridge.mix,
        "price": bridge.price,
        "cost": bridge.cost,
    }
    if gap == 0:
        return "Gross profit landed exactly on budget; the four drivers net to zero."
    if gap < 0:
        driver, value = min(components.items(), key=lambda item: item[1])
        share = abs(value / gap * 100)
        story = (
            f"{driver.capitalize()} is {share:.0f}% of the "
            f"{money.compact(abs(gap))} shortfall"
        )
        favourable = [name for name, amount in components.items() if amount > 0]
        if len(favourable) == 1:
            story += f"; {favourable[0]} is the only driver in the business's favour"
        elif favourable:
            names = " and ".join(favourable)
            story += f"; {names} are the only drivers in the business's favour"
        return story + "."
    driver, value = max(components.items(), key=lambda item: item[1])
    return (
        f"Gross profit is {money.compact(gap)} above budget, led by "
        f"{driver} ({_signed(value)})."
    )


def bridge_waterfall(analysis: MonthAnalysis, path: Path) -> Path:
    """Budget to actual, one bar per driver, each labelled with its share."""
    bridge = analysis.bridge
    steps = [
        ("Budget", float(bridge.budget_gp), bridge.budget_gp, None),
        ("Volume", float(bridge.volume), bridge.volume, bridge.volume),
        ("Mix", float(bridge.mix), bridge.mix, bridge.mix),
        ("Price", float(bridge.price), bridge.price, bridge.price),
        ("Cost", float(bridge.cost), bridge.cost, bridge.cost),
        ("Actual", float(bridge.actual_gp), bridge.actual_gp, None),
    ]

    img, draw = _canvas(
        f"Gross profit bridge - {analysis.month}",
        f"Budget {money.compact(bridge.budget_gp)} to actual "
        f"{money.compact(bridge.actual_gp)}. {_shortfall_story(analysis)}",
    )

    # Geometry is fixed so the chart's own regression test can read the bars
    # back out by scanning columns of pixels.
    left, right, top, bottom = 90, WIDTH - 90, 170, HEIGHT - 90

    # The axis starts just below the lowest point the bridge reaches, not at
    # zero: the deltas are a few percent of a million-shilling level, and a
    # zero baseline would flatten the story into unreadable slabs.
    walk = [float(bridge.budget_gp)]
    running = float(bridge.budget_gp)
    for _, value, _, delta in steps:
        if delta is not None:
            running += value
            walk.append(running)
    low = min(walk) * 0.985
    high = max(walk) * 1.015
    span = high - low or 1.0

    def y_of(value: float) -> float:
        return bottom - (value - low) / span * (bottom - top)

    for step in range(5):
        value = low + span * step / 4
        y = y_of(value)
        draw.line([(left, y), (right, y)], fill=GRID, width=1)
        draw.text((26, y - 8), money.compact(value), font=_font(12), fill=MUTED)

    gap = bridge.total_variance
    slot = (right - left) / len(steps)
    bar_width = slot * 0.52
    # The first delta bar starts at budget gross profit, not at zero: that is
    # what makes the picture a bridge rather than five unrelated columns.
    running = float(bridge.budget_gp)
    for index, (label, value, exact, delta) in enumerate(steps):
        cx = left + slot * index + slot / 2
        if delta is None:
            top_y = y_of(value)
            bottom_y = bottom
            colour = ACCENT
            _centred(draw, cx, top_y - 26, money.compact(exact), _font(15), INK)
        else:
            start = running
            running += value
            top_y = y_of(max(start, running))
            bottom_y = y_of(min(start, running))
            colour = GOOD if value >= 0 else WARN
            _centred(draw, cx, top_y - 48, _signed(exact), _font(15), colour)
            if gap:
                share = abs(exact / gap * 100)
                note = f"{share:.0f}% of gap" if exact <= 0 else f"{share:.0f}% offset"
                _centred(draw, cx, top_y - 28, note, _font(12), MUTED)
            draw.line(
                [(cx - bar_width / 2, y_of(start)), (cx + bar_width / 2, y_of(start))],
                fill=GRID,
                width=1,
            )
        draw.rectangle(
            [cx - bar_width / 2, top_y, cx + bar_width / 2, bottom_y],
            fill=colour,
            outline=None,
        )
        draw.text((cx - 26, bottom + 14), label, font=_font(15), fill=INK)

    # Legend, so the two colours are never guessed at.
    legend_y = 138
    for offset, colour, text in (
        (0, ACCENT, "budget and actual"),
        (196, GOOD, "favourable driver"),
        (376, WARN, "unfavourable driver"),
    ):
        draw.rectangle([left + offset, legend_y, left + offset + 12, legend_y + 12], fill=colour)
        draw.text((left + offset + 20, legend_y - 2), text, font=_font(13), fill=MUTED)

    draw.line([(left, bottom), (right, bottom)], fill=MUTED, width=1)
    draw.text(
        (left, HEIGHT - 44),
        f"Axis starts at {money.compact(low)}, not zero. Each bar carries its "
        f"value and its share of the {money.compact(abs(gap))} gap.",
        font=_font(13),
        fill=MUTED,
    )
    return _save(img, path)


def gross_profit_trend(analysis: MonthAnalysis, trend_rows, path: Path) -> Path:
    """Actual against budget over time, with the current month labelled."""
    recent = [row for row in trend_rows[-6:]]
    below = sum(1 for row in recent if row["actual_gross_profit"] < row["budget_gross_profit"])
    gap = analysis.gross_profit_variance
    if below == len(recent):
        record = "every one of the last six months below plan"
    else:
        record = f"{below} of the last six months below plan"

    img, draw = _canvas(
        "Gross profit against budget",
        f"Eighteen months of actual against the phased budget - {record}, "
        f"{analysis.month} {money.compact(gap)} against budget.",
    )
    left, right, top, bottom = 110, WIDTH - 90, 180, HEIGHT - 110
    values = [float(r["budget_gross_profit"]) for r in trend_rows] + [
        float(r["actual_gross_profit"]) for r in trend_rows
    ]
    low, high = min(values) * 0.92, max(values) * 1.06
    span = high - low or 1.0

    for step in range(5):
        value = low + span * step / 4
        y = bottom - (value - low) / span * (bottom - top)
        draw.line([(left, y), (right, y)], fill=GRID, width=1)
        draw.text((60, y - 8), money.compact(value), font=_font(13), fill=MUTED)

    step_x = (right - left) / max(len(trend_rows) - 1, 1)

    def series(name):
        return [
            (left + step_x * i, bottom - (float(row[name]) - low) / span * (bottom - top))
            for i, row in enumerate(trend_rows)
        ]

    budget_points = series("budget_gross_profit")
    actual_points = series("actual_gross_profit")

    draw.line(budget_points, fill=ACCENT_SOFT, width=3)
    draw.line(actual_points, fill=ACCENT, width=3)

    for x, y in actual_points:
        draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=ACCENT)

    index = [row["month"] for row in trend_rows].index(analysis.month)
    x = left + step_x * index
    draw.line([(x, top), (x, bottom)], fill=WARN, width=1)
    draw.text((x - 46, top - 22), analysis.month, font=_font(13), fill=WARN)

    # The gap bracket: the distance between plan and actual, labelled.
    actual_y = actual_points[index][1]
    budget_y = budget_points[index][1]
    bracket_x = x + 16
    draw.line([(bracket_x, budget_y), (bracket_x, actual_y)], fill=WARN, width=2)
    for y in (budget_y, actual_y):
        draw.line([(bracket_x - 5, y), (bracket_x + 5, y)], fill=WARN, width=2)
    if abs(actual_y - budget_y) > 26:
        draw.text(
            (bracket_x + 8, (budget_y + actual_y) / 2 - 8),
            f"gap {money.compact(abs(gap))}",
            font=_font(12),
            fill=WARN,
        )
    _right_aligned(
        draw, x - 14, actual_y + 10, money.compact(analysis.actual_gross_profit), _font(12), ACCENT
    )
    _right_aligned(
        draw, x - 14, budget_y - 20, money.compact(analysis.budget_gross_profit), _font(12), MUTED
    )

    for i, row in enumerate(trend_rows):
        if i % 3 == 0 or i == len(trend_rows) - 1:
            x = left + step_x * i
            draw.text((x - 26, bottom + 12), row["month"], font=_font(11), fill=MUTED)

    # Legend on the left, clear of the month marker at the right edge.
    draw.text((left, 148), "- actual", font=_font(15), fill=ACCENT)
    draw.text((left + 96, 148), "- budget", font=_font(15), fill=ACCENT_SOFT)
    draw.text(
        (left, HEIGHT - 54),
        "Same seeded ledger; budget re-phased each January.",
        font=_font(13),
        fill=MUTED,
    )
    return _save(img, path)


def variance_by_owner(analysis: MonthAnalysis, path: Path) -> Path:
    """Each driver attributed to the department that can act on it."""
    owners = bridge_mod.owner_totals(analysis.bridge)
    gap = analysis.gross_profit_variance
    largest = max(owners, key=lambda name: abs(owners[name]))
    share = abs(owners[largest] / gap * 100) if gap else 0
    favourable = sum(1 for value in owners.values() if value > 0)

    img, draw = _canvas(
        "Who owns the variance",
        f"{largest} carries {share:.0f}% of the {money.compact(abs(gap))} gap; "
        f"{favourable} of {len(owners)} departments "
        f"{'is' if favourable == 1 else 'are'} in the business's favour.",
    )
    name_x, zero_x, value_x = 70, 560, 860
    top, bottom = 180, HEIGHT - 90
    names = list(owners)
    values = [float(owners[name]) for name in names]
    span = max(abs(v) for v in values) or 1.0
    scale = 240 / span

    row_height = (bottom - top) / len(names)
    for index, (name, value) in enumerate(zip(names, values)):
        cy = top + row_height * index + row_height * 0.30
        width = abs(value) * scale
        colour = GOOD if value >= 0 else WARN
        if value >= 0:
            draw.rectangle([zero_x, cy, zero_x + width, cy + 34], fill=colour)
        else:
            draw.rectangle([zero_x - width, cy, zero_x, cy + 34], fill=colour)
        draw.text((name_x, cy + 6), name, font=_font(16), fill=INK)
        draw.text((value_x, cy + 6), _signed(owners[name]), font=_font(15), fill=colour)
        if gap:
            part = abs(owners[name] / gap * 100)
            draw.text((value_x + 100, cy + 8), f"{part:.0f}%", font=_font(13), fill=MUTED)

    draw.line([(zero_x, top), (zero_x, bottom)], fill=MUTED, width=1)
    draw.text((value_x + 100, top - 24), "share of gap", font=_font(12), fill=MUTED)
    for offset, colour, text in (
        (0, GOOD, "favourable"),
        (140, WARN, "unfavourable"),
    ):
        draw.rectangle([name_x + offset, 148, name_x + offset + 12, 160], fill=colour)
        draw.text((name_x + offset + 20, 146), text, font=_font(13), fill=MUTED)
    draw.text(
        (value_x - 300, 148),
        "Each bar is one department's contribution to the gap.",
        font=_font(13),
        fill=MUTED,
    )
    draw.text(
        (name_x, HEIGHT - 52),
        f"Total variance {money.compact(gap)} - the four bars sum to it.",
        font=_font(13),
        fill=MUTED,
    )
    return _save(img, path)
