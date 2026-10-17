"""Report charts, rendered to repo-local PNG files.

Charts are illustrative; every number they show comes from the same analysis the
answer key is built from. They are drawn with Pillow so the output is a plain
file in the repository, never a hosted embed.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import variance

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
    draw.text((70, 46), title, font=_font(30), fill=INK)
    draw.text((70, 88), subtitle, font=_font(16), fill=MUTED)
    return img, draw


def _money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}{value / 1_000_000:,.2f}M"
    if value >= 1_000:
        return f"{sign}{value / 1_000:,.0f}K"
    return f"{sign}{value:,.0f}"


def _save(img, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)
    return path


def bridge_waterfall(analysis: variance.MonthAnalysis, path: Path) -> Path:
    bridge = analysis.bridge
    steps = [
        ("Budget", float(bridge.budget_gp), None),
        ("Volume", float(bridge.volume), float(bridge.volume)),
        ("Mix", float(bridge.mix), float(bridge.mix)),
        ("Price", float(bridge.price), float(bridge.price)),
        ("Cost", float(bridge.cost), float(bridge.cost)),
        ("Actual", float(bridge.actual_gp), None),
    ]

    img, draw = _canvas(
        "Gross profit bridge",
        f"{analysis.month}: budget to actual, split into four drivers that reconcile to the cent",
    )

    left, right, top, bottom = 90, WIDTH - 90, 170, HEIGHT - 90
    values = [v for _, v, _ in steps if v is not None]
    high = max(max(values), float(bridge.budget_gp), float(bridge.actual_gp)) * 1.08
    low = min(0.0, float(bridge.actual_gp)) * 1.08
    span = high - low or 1.0

    def y_of(value: float) -> float:
        return bottom - (value - low) / span * (bottom - top)

    slot = (right - left) / len(steps)
    bar_width = slot * 0.52
    running = 0.0
    for index, (label, value, delta) in enumerate(steps):
        cx = left + slot * index + slot / 2
        if delta is None:
            top_y = y_of(max(value, 0.0))
            bottom_y = y_of(min(value, 0.0))
            colour = ACCENT
            draw.text((cx - 20, top_y - 26), _money(value), font=_font(15), fill=INK)
        else:
            start = running
            running += value
            top_y = y_of(max(start, running))
            bottom_y = y_of(min(start, running))
            colour = GOOD if value >= 0 else WARN
            draw.text(
                (cx - 20, top_y - 26),
                f"{'+' if value >= 0 else ''}{_money(value)}",
                font=_font(15),
                fill=colour,
            )
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

    draw.line([(left, bottom), (right, bottom)], fill=MUTED, width=1)
    draw.text(
        (left, HEIGHT - 44),
        "Synthetic ledger: " + analysis.month,
        font=_font(13),
        fill=MUTED,
    )
    return _save(img, path)


def gross_profit_trend(analysis: variance.MonthAnalysis, trend_rows, path: Path) -> Path:
    img, draw = _canvas(
        "Gross profit against budget",
        "Eighteen months of actual gross profit against the phased budget",
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
        draw.text((60, y - 8), _money(value), font=_font(13), fill=MUTED)

    step_x = (right - left) / max(len(trend_rows) - 1, 1)

    def series(key):
        return [
            (left + step_x * i, bottom - (float(row[key]) - low) / span * (bottom - top))
            for i, row in enumerate(trend_rows)
        ]

    budget_points = series("budget_gross_profit")
    actual_points = series("actual_gross_profit")

    draw.line(budget_points, fill=ACCENT_SOFT, width=3)
    draw.line(actual_points, fill=ACCENT, width=3)

    for i, row in enumerate(trend_rows):
        if row["month"] == analysis.month:
            x = left + step_x * i
            draw.line([(x, top), (x, bottom)], fill=WARN, width=1)
            draw.text((x - 42, top - 22), analysis.month, font=_font(13), fill=WARN)

    draw.text((right - 210, 150), "— actual", font=_font(15), fill=ACCENT)
    draw.text((right - 110, 150), "— budget", font=_font(15), fill=ACCENT_SOFT)
    draw.text(
        (left, HEIGHT - 54),
        "Same seeded ledger; budget re-phased each January.",
        font=_font(13),
        fill=MUTED,
    )
    return _save(img, path)


def variance_by_owner(analysis: variance.MonthAnalysis, path: Path) -> Path:
    owners = variance.owner_totals(analysis.bridge)
    img, draw = _canvas(
        "Who owns the variance",
        "Each driver attributed to the department that can act on it",
    )
    name_x, zero_x, value_x = 70, 560, 880
    top, bottom = 170, HEIGHT - 90
    names = list(owners)
    values = [float(owners[name]) for name in names]
    span = max(abs(v) for v in values) or 1.0
    scale = 250 / span

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
        draw.text((value_x, cy + 6), _money(value), font=_font(15), fill=colour)

    draw.line([(zero_x, top), (zero_x, bottom)], fill=MUTED, width=1)
    draw.text(
        (name_x, HEIGHT - 52),
        f"Total variance {_money(float(analysis.gross_profit_variance))} — the four bars sum to it.",
        font=_font(13),
        fill=MUTED,
    )
    return _save(img, path)
