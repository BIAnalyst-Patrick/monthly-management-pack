"""Build the human deliverables: the local report, the brief, a PDF and a deck.

    PYTHONPATH=.venv-site python3 scripts/build_docs.py

The markdown is standard library only. The PDF needs reportlab and the deck
needs python-pptx; both are optional extras listed in requirements-docs.txt, and
the command fails with a clear message if they are missing.

Every document is written from the same answer key the published pack uses, so a
figure cannot disagree between the markdown, the PDF and the slides. Both binary
formats are normalised before saving: identical inputs produce identical bytes,
which is what lets `make test` compare them.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import zipfile
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pack import generator, key as key_mod, money, trends  # noqa: E402
from pack import exceptions as exceptions_mod  # noqa: E402
from pack.analysis import analyse_month  # noqa: E402
from pack.model import MONTHS, Ledger  # noqa: E402

MONTH = "2026-06"
CHARTS = ROOT / "outputs" / "charts"
ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

NAVY = (11, 94, 132)
INK = (23, 32, 42)
MUTED = (110, 124, 140)
GOOD = (21, 128, 92)
WARN = (176, 58, 46)
LIGHT = (240, 244, 248)


def _esc(text: str) -> str:
    for char, entity in ESC.items():
        text = text.replace(char, entity)
    return text


def _table(headers, rows, numeric=None) -> str:
    """A markdown table; ``numeric`` names the columns to right-align."""
    numeric = set(range(1, len(headers))) if numeric is None else set(numeric)
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(
        "---:" if index in numeric else "---" for index in range(len(headers))
    ) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def _actions(key, limit=4):
    return key["exceptions"][:limit]


def _owner_rows(key):
    gap = Decimal(key["bridge"]["total"])
    rows = []
    for owner, value in key["owners"].items():
        share = abs(Decimal(value) / gap * 100) if gap else Decimal(0)
        rows.append((owner, money.grouped(value), f"{share:.0f}%"))
    return rows


def _line_insight(lines, gap) -> str:
    """What the worst ten lines have in common, stated as a sentence."""
    top = lines[:10]
    if not top:
        return "No line crossed the reporting threshold this month."
    top_total = sum((Decimal(row["variance"]) for row in top), Decimal(0))
    branch, branch_count = Counter(row["branch"] for row in top).most_common(1)[0]
    owner, owner_count = Counter(row["owner"] for row in top).most_common(1)[0]
    worst = top[0]
    return (
        f"The ten worst lines account for {money.grouped(abs(top_total))} of the "
        f"{money.grouped(abs(gap))} gap. {branch_count} of them sit in {branch}, and "
        f"{owner} owns {owner_count}. The single worst is {worst['product']} in "
        f"{worst['branch']} at {money.grouped(worst['variance'])}."
    )


def report_markdown(analysis, key) -> str:
    """The local management report, as markdown with the committed charts."""
    headline = key["headline"]
    bridge = key["bridge"]
    gap = Decimal(bridge["total"])
    budget_gp = Decimal(bridge["budget_gross_profit"])
    lines = [
        f"# Monthly management report - {analysis.month}",
        "",
        f"> **Synthetic data.** Every figure here is generated from a seeded, documented "
        f"mechanism (ledger fingerprint `{key['fingerprint']}`). No client figures appear "
        f"in this report. Regenerate it with `make docs`.",
        "",
        "## The headline",
        "",
        _table(
            ["Measure", "Budget", "Actual", "Variance", "%"],
            [
                ("Revenue", money.grouped(headline["revenue_budget"]),
                 money.grouped(headline["revenue_actual"]),
                 money.grouped(headline["revenue_variance"]),
                 f"{headline['revenue_variance_pct']}%"),
                ("Gross profit", money.grouped(headline["gross_profit_budget"]),
                 money.grouped(headline["gross_profit_actual"]),
                 money.grouped(headline["gross_profit_variance"]),
                 f"{headline['gross_profit_variance_pct']}%"),
            ],
        ),
        "",
        f"Revenue missed budget by {abs(Decimal(headline['revenue_variance_pct']))}%; "
        f"gross profit missed it by {abs(Decimal(headline['gross_profit_variance_pct']))}%, "
        f"a shortfall of "
        f"{money.kes(abs(gap), absolute=True)}. The business sold roughly the volume it "
        f"planned and kept far less of the money, and the largest single driver is "
        f"**{headline['largest_driver']}**.",
        "",
        "![Gross profit bridge](../outputs/charts/01_bridge_waterfall.png)",
        "",
        "## The bridge",
        "",
        _table(
            ["Driver", "KES", "Share of budget gross profit"],
            [
                ("Volume - total units at budget margin per unit",
                 money.grouped(bridge["volume"]),
                 f"{money.cents(Decimal(bridge['volume']) / budget_gp * 100)}%"),
                ("Mix - selling a different blend at budget margins",
                 money.grouped(bridge["mix"]),
                 f"{money.cents(Decimal(bridge['mix']) / budget_gp * 100)}%"),
                ("Price - actual units at the change in selling price",
                 money.grouped(bridge["price"]),
                 f"{money.cents(Decimal(bridge['price']) / budget_gp * 100)}%"),
                ("Cost - actual units at the change in unit cost",
                 money.grouped(bridge["cost"]),
                 f"{money.cents(Decimal(bridge['cost']) / budget_gp * 100)}%"),
                ("**Total variance**", f"**{money.grouped(gap)}**", ""),
            ],
        ),
        "",
        f"The four drivers sum to {money.grouped(gap)} to the cent. The flexed budget - "
        f"actual volume at budget price and cost - is "
        f"{money.grouped(bridge['flexed_gross_profit'])}; volume and mix account for the "
        f"difference between budget and flex, price and cost for the difference between "
        f"flex and actual.",
        "",
        "## Who owns it",
        "",
        _table(["Department", "Variance (KES)", "Share of gap"], _owner_rows(key)),
        "",
        "![Who owns the variance](../outputs/charts/03_variance_by_owner.png)",
        "",
        "## Branches, judged on a trend basis",
        "",
        _table(
            ["Branch", "Units vs budget", "Rolling gap % (+ ahead)", "Adverse months", "Off track"],
            [
                (row["branch"], f"{row['units_actual'] - row['units_budget']:+d}",
                 row["variance_pct"], row["adverse_months"],
                 "yes" if row["off_track"] else "no")
                for row in key["branch_trends"]
            ],
        ),
        "",
        "![Gross profit against budget](../outputs/charts/02_gross_profit_trend.png)",
        "",
        "## Line level - the ten worst lines",
        "",
        _table(
            ["Branch", "Product", "Variance", "Price", "Unit cost", "Volume", "Owner"],
            [
                (row["branch"], row["product"], money.grouped(row["variance"]),
                 money.grouped(row["price"]), money.grouped(row["cost_rate"]),
                 money.grouped(Decimal(row["volume_revenue"]) + Decimal(row["volume_cost"])),
                 row["owner"])
                for row in key["lines"][:10]
            ],
            numeric={2, 3, 4, 5},
        ),
        "",
        _line_insight(key["lines"], gap),
        "",
        f"All {len(key['lines'])} lines are published with their four components in "
        "[`outputs/tables/line_variance.csv`](../outputs/tables/line_variance.csv).",
        "",
        "## What I would do first",
        "",
    ]
    for index, row in enumerate(_actions(key), start=1):
        lines.append(
            f"{index}. **{row['owner']}** - {row['action']}. Worth "
            f"{money.kes(abs(Decimal(row['gross_profit_impact'])), absolute=True)} of gross "
            f"profit, review date the last working day of next month. "
            f"{row['finding']}"
        )
    lines += [
        "",
        "## Method and limits",
        "",
        "- Volume is total units at budget gross profit per unit; mix is the residual, so "
        "the four parts reconcile exactly rather than approximately.",
        "- Gross profit only: no overhead allocation, no tax, no foreign exchange, no "
        "write-offs. This is a trading pack, not a P&L.",
        "- The ledger is synthetic and seeded; the fingerprint proves which ledger produced "
        "these numbers.",
        f"- {len(key['lines'])} product lines, three branches, eighteen months, and the "
        "seventeen checks in [`outputs/validation_report.md`](../outputs/validation_report.md).",
        "",
        "## How this pack is produced",
        "",
        "The monthly cycle, the thresholds and what a human still has to decide are set out "
        "in [how-a-management-pack-is-produced.md](how-a-management-pack-is-produced.md). "
        "This month's PDF and slide deck are in the same folder.",
        "",
    ]
    return "\n".join(lines)


def brief_markdown(key) -> str:
    """The real-world briefing: how a management pack is actually run."""
    exceptions = key["exceptions"]
    materiality = money.grouped(key["materiality"])
    trend = key["branch_trends"]
    off_track = [row["branch"] for row in trend if row["off_track"]]
    lines = [
        "# How a monthly management pack is produced",
        "",
        "A management pack is not a dashboard and not a set of accounts. It is the one "
        "document a leadership team reads to decide what to change this month, and it is "
        "judged by whether it answers three questions: **what moved, what caused it, and "
        "who is going to do something about it.** This is the cycle behind the pack in "
        "this repository, written the way it runs in a trading business.",
        "",
        "## 1. Days 1-2: close and lock the data",
        "",
        "- Sales and margin are cut from the transaction system, purchases from the "
        "purchase ledger, and both are tied back to the general ledger control accounts "
        "before anything is analysed. An unreconciled close makes every later number "
        "arguable.",
        "- The budget register is frozen for the year. If the plan is re-phased in the "
        "analysis, the variance stops being a performance measure and becomes a "
        "negotiation.",
        "- The dataset is fingerprinted. Here a SHA-256 over the canonical ledger stands in "
        "for the month-end lock: a hand-edited line no longer matches its fingerprint and "
        "the published checks fail.",
        "",
        "## 2. Day 2: flex the budget before judging anyone",
        "",
        "Comparing actual gross profit with a fixed budget confuses three different "
        "failures. The flexed budget - actual volume at budget price and budget cost - "
        "splits the movement cleanly:",
        "",
        "- **Volume** is total units at the budget's gross profit per unit.",
        "- **Mix** is what is left of the volume movement once total units are removed: the "
        "effect of selling a different blend.",
        "- **Price** is actual units at the change in selling price, so a discount shows up "
        "even on a line that sold exactly to plan.",
        "- **Cost** is actual units at the change in unit cost, which is what separates "
        "supplier inflation from a branch that cannot sell.",
        "",
        "The four components are defined to sum to the total to the cent. That identity is "
        "the control: if they do not reconcile, the decomposition is wrong, not "
        "approximately right.",
        "",
        "## 3. Day 3: decompose to the line, then assign an owner",
        "",
        "A portfolio-level bridge tells the board what happened; it does not tell anyone "
        "what to do. The pack therefore decomposes every product line in every branch and "
        f"attributes each one - {len(key['lines'])} lines here - to the department that can "
        "move its largest component: Commercial / Pricing for price, Procurement for cost, "
        "Branch Sales for volume. Mix stays at portfolio level, because no single product "
        "manager owns the blend.",
        "",
        "Ownership is assigned by arithmetic, not by opinion, which is what makes it "
        "defensible in the meeting: the rule is published, so an owner can argue with the "
        "numbers but not with the method.",
        "",
        "## 4. Day 3: escalate only what is material",
        "",
        "A pack that lists everything gets read as noise. Exceptions are selected by "
        "threshold and ranked by gross-profit impact:",
        "",
        f"- Materiality: **{materiality} KES** of gross profit.",
        "- Price erosion: realised price below **97.5%** of the budgeted price on the "
        "volume actually sold.",
        "- Cost step: unit cost above **102.5%** of budget on the volume bought.",
        "- Branch trend: below budget on units in **at least 2 of the last 3 months**, with "
        "a rolling gap of **5%** or more. Reading units rather than profit matters - a "
        "branch discounting its way to a miss has a pricing problem, not a trading one.",
        "",
        f"This month that produces {len(exceptions)} exceptions"
        + (f", and {', '.join(off_track)} is the branch off track." if off_track else "."),
        "",
        "## 5. Day 4: write the pack in reading order",
        "",
        "1. **The headline** - two lines: what the result was, and how far off plan.",
        "2. **The bridge** - where the gap came from, in four components that reconcile.",
        "3. **Where it sits** - branch, category and the worst lines, with names attached.",
        "4. **The actions** - owner, action, value at stake, review date. No action without "
        "an owner; no owner without a date.",
        "",
        "Every figure in the narrative is generated from the same answer key as the tables, "
        "so the prose cannot drift from the numbers. The charts carry their own labels for "
        "the same reason: a reader should not need the table to understand the picture.",
        "",
        "## 6. Day 4-5: the meeting, then the register",
        "",
        "The pack exists to be argued with in a 45-minute meeting with three outputs: the "
        "two or three actions that get funded, the owner and date for each, and anything "
        "that needs a decision above the meeting's authority. Last month's actions are the "
        "first item on the agenda, not the last - otherwise the pack becomes a monthly "
        "description of the same problem.",
        "",
        "## 7. Controls a reader should expect",
        "",
        "- The bridge reconciles to the cent, and the line table reconciles to the bridge.",
        "- Budget and actuals cover exactly the same lines; a missing line is a failure, not "
        "a zero.",
        "- The answer key is checked against a recomputation, not against itself.",
        "- Every published figure is reproducible from the ledger with one command. Here "
        "that is `make run`, and the seventeen checks are published rather than asserted.",
        "",
        "## 8. What this repository automates, and what it does not",
        "",
        "Automated: the ledger, the flex, the bridge, the decomposition, ownership, "
        "exception selection, the tables, the charts, the validation report, this brief's "
        "figures, and the PDF and slide exports.",
        "",
        "Not automated, and deliberately so: deciding whether a price move was a mistake or "
        "a strategy, judging whether a cost step is temporary, choosing which actions to "
        "fund, and fixing the data-quality problems that a close always finds. A pack "
        "that pretends to decide those things is a pack nobody trusts.",
        "",
        "## 9. This month, in one line",
        "",
        f"Gross profit missed budget by {money.kes(abs(Decimal(key['headline']['gross_profit_variance'])), absolute=True)} "
        f"({key['headline']['gross_profit_variance_pct']}%); price is the largest driver and "
        f"{exceptions[0]['owner'] if exceptions else 'no department'} owns the first action. "
        "Read the [report](report-2026-06.md), the [PDF](monthly-pack-2026-06.pdf) or the "
        "[deck](monthly-pack-2026-06.pptx).",
        "",
    ]
    return "\n".join(lines)


def _pdf_paths():
    try:
        import reportlab  # noqa: F401
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as error:  # pragma: no cover - optional dependency
        raise SystemExit(
            "The PDF needs reportlab. Install the docs extras: "
            "python3 -m pip install --target .venv-site -r requirements-docs.txt "
            "then run with PYTHONPATH=.venv-site"
        ) from error
    return colors, landscape(A4), ParagraphStyle, getSampleStyleSheet, mm, (
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )


def build_pdf(analysis, key, path: Path) -> Path:
    """The management report as a print-ready PDF."""
    import reportlab.rl_config

    reportlab.rl_config.invariant = 1
    colors, pagesize, ParagraphStyle, getSampleStyleSheet, mm, flow = _pdf_paths()
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle = flow

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6,
        leading=14, textColor=colors.HexColor("#17202A"), spaceAfter=4,
    )
    h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=26,
        leading=30, textColor=colors.HexColor("#0B5E84"), spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14,
        leading=18, textColor=colors.HexColor("#17202A"), spaceBefore=10, spaceAfter=4,
    )
    small = ParagraphStyle(
        "Small", parent=body, fontSize=8.2, leading=11, textColor=colors.HexColor("#6E7C8C"),
    )
    kpi = ParagraphStyle(
        "KPI", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=26,
        textColor=colors.HexColor("#17202A"), alignment=1,
    )
    kpi_label = ParagraphStyle(
        "KPILabel", parent=small, alignment=1,
    )

    headline = key["headline"]
    bridge = key["bridge"]
    gap = Decimal(bridge["total"])

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#6E7C8C"))
        canvas.drawString(
            16 * mm, 10 * mm,
            f"Monthly management pack - {key['month']}  |  ledger {key['fingerprint']}  |  "
            "synthetic data",
        )
        canvas.drawRightString(281 * mm, 10 * mm, f"page {doc.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(path), pagesize=pagesize, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm,
        title=f"Monthly management pack - {key['month']}", author="Sting Analytics",
    )
    story = []

    story.append(Paragraph("Monthly management pack", h1))
    story.append(Paragraph(f"{key['month']} - prepared from the seeded synthetic ledger", body))
    story.append(Spacer(1, 10))
    story.append(
        Table(
            [
                [
                    Paragraph(money.grouped(gap), kpi),
                    Paragraph(f"{headline['gross_profit_variance_pct']}%", kpi),
                    Paragraph(f"{headline['revenue_variance_pct']}%", kpi),
                    Paragraph(f"{len(key['lines'])}", kpi),
                ],
                [
                    Paragraph("gross profit variance (KES)", kpi_label),
                    Paragraph("gross profit vs budget", kpi_label),
                    Paragraph("revenue vs budget", kpi_label),
                    Paragraph("product lines with an owner", kpi_label),
                ],
            ],
            colWidths=[64 * mm] * 4,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE6")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D6DEE6")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        )
    )
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f"Revenue came in {abs(Decimal(headline['revenue_variance_pct']))}% off budget; "
            f"gross profit came in {abs(Decimal(headline['gross_profit_variance_pct']))}% "
            f"off it. The "
            f"largest driver is {headline['largest_driver']}, and the four drivers "
            f"reconcile to the cent. This pack decomposes all {len(key['lines'])} lines, "
            "attributes each to a department and names the owner of every action.",
            body,
        )
    )
    story.append(Spacer(1, 6))
    story.append(Image(str(CHARTS / "01_bridge_waterfall.png"), width=262 * mm, height=148 * mm))
    story.append(Paragraph("The bridge: budget to actual, four drivers, each labelled.", small))
    story.append(PageBreak())

    story.append(Paragraph("Where the profit went", h2))
    rows = [["Driver", "KES", "Share of budget GP"]]
    budget_gp = Decimal(bridge["budget_gross_profit"])
    for name, label in (
        ("volume", "Volume - total units at budget margin per unit"),
        ("mix", "Mix - a different blend at budget margins"),
        ("price", "Price - actual units at the change in selling price"),
        ("cost", "Cost - actual units at the change in unit cost"),
    ):
        value = Decimal(bridge[name])
        rows.append(
            [Paragraph(label, body), money.grouped(value),
             f"{money.cents(value / budget_gp * 100)}%"]
        )
    rows.append(["Total variance", money.grouped(gap), ""])
    story.append(
        Table(
            rows,
            colWidths=[156 * mm, 58 * mm, 48 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E84")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F7F9FB")]),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
    )
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            f"Flexed budget - actual volume at budget price and cost - is "
            f"{money.grouped(bridge['flexed_gross_profit'])}. Volume plus mix explains the "
            "difference from budget; price plus cost explains the difference from the flex.",
            body,
        )
    )
    story.append(Paragraph("Who owns it", h2))
    owner_rows = [["Department", "Variance (KES)", "Share of gap"]]
    owner_rows += [[row[0], row[1], row[2]] for row in _owner_rows(key)]
    story.append(
        Table(
            owner_rows,
            colWidths=[120 * mm, 72 * mm, 70 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E84")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            ),
        )
    )
    story.append(Paragraph("Branches, judged on a trend basis", h2))
    trend_rows = [["Branch", "Units vs budget", "Rolling gap % (+ ahead)", "Adverse months", "Off track"]]
    for row in key["branch_trends"]:
        trend_rows.append(
            [row["branch"], f"{row['units_actual'] - row['units_budget']:+d}",
             f"{row['variance_pct']}%", str(row["adverse_months"]),
             "yes" if row["off_track"] else "no"]
        )
    story.append(
        Table(
            trend_rows,
            colWidths=[82 * mm, 55 * mm, 58 * mm, 40 * mm, 25 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E84")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            ),
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("The ten worst lines", h2))
    line_rows = [["Branch", "Product", "Variance", "Price", "Unit cost", "Owner"]]
    for row in key["lines"][:10]:
        line_rows.append(
            [row["branch"], row["product"], money.grouped(row["variance"]),
             money.grouped(row["price"]), money.grouped(row["cost_rate"]), row["owner"]]
        )
    story.append(
        Table(
            line_rows,
            colWidths=[40 * mm, 74 * mm, 38 * mm, 38 * mm, 38 * mm, 34 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E84")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (2, 0), (4, -1), "RIGHT"),
                ]
            ),
        )
    )
    story.append(Paragraph(_esc(_line_insight(key["lines"], gap)), body))
    story.append(Paragraph(
        f"All {len(key['lines'])} lines with price, unit-cost, volume and owner are in "
        "outputs/tables/line_variance.csv.", small,
    ))
    story.append(Spacer(1, 6))
    story.append(Image(str(CHARTS / "03_variance_by_owner.png"), width=262 * mm, height=148 * mm))
    story.append(Paragraph("Every department's contribution to the gap, with its share.", small))
    story.append(Image(str(CHARTS / "02_gross_profit_trend.png"), width=262 * mm, height=148 * mm))
    story.append(Paragraph("Actual against the phased budget, with the current gap labelled.", small))
    story.append(PageBreak())

    story.append(Paragraph("What I would do first", h2))
    actions = [["Owner", "Action", "Value (KES)"]]
    for row in _actions(key):
        actions.append(
            [row["owner"], Paragraph(_esc(row["action"]), body),
             money.grouped(abs(Decimal(row["gross_profit_impact"])))]
        )
    story.append(
        Table(
            actions,
            colWidths=[52 * mm, 174 * mm, 36 * mm],
            style=TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B5E84")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6DEE6")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ]
            ),
        )
    )
    story.append(Paragraph("The evidence behind each action", h2))
    for row in _actions(key):
        story.append(Paragraph(f"<b>{_esc(row['label'])}</b> - {_esc(row['finding'])}", body))

    story.append(Paragraph("Method and limits", h2))
    for text in (
        "Volume is total units at budget gross profit per unit; mix is the residual, so the "
        "four parts reconcile to the cent rather than approximately.",
        "Gross profit only: no overhead allocation, no tax, no foreign exchange, no "
        "write-offs. This is a trading pack, not a P&L.",
        "The ledger is synthetic and seeded; the fingerprint proves which ledger produced "
        "these numbers, and a hand-edited line fails the published checks.",
        f"{len(key['lines'])} product lines, three branches, eighteen months, and seventeen "
        "published checks over sixteen distinct identities.",
        "Regenerate the pack with make run; rebuild this PDF and the deck with make docs.",
    ):
        story.append(Paragraph(f"- {_esc(text)}", body))

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return path


def _normalise_zip(path: Path) -> None:
    """Rewrite a package with fixed timestamps so identical input gives identical bytes."""
    with zipfile.ZipFile(path) as source:
        entries = [(info.filename, source.read(info)) for info in source.infolist()]
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as target:
        for name, blob in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 6, 30, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, blob)


def build_pptx(analysis, key, path: Path) -> Path:
    """An eight-slide deck: the same story, told in a meeting."""
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        from pptx.util import Inches, Pt
    except ImportError as error:  # pragma: no cover - optional dependency
        raise SystemExit(
            "The deck needs python-pptx. Install the docs extras: "
            "python3 -m pip install --target .venv-site -r requirements-docs.txt "
            "then run with PYTHONPATH=.venv-site"
        ) from error

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    ink = RGBColor(*INK)
    muted = RGBColor(*MUTED)
    navy = RGBColor(*NAVY)
    warn = RGBColor(*WARN)
    light = RGBColor(*LIGHT)
    white = RGBColor(255, 255, 255)

    def text(slide, left, top, width, height, value, size=18, bold=False, colour=ink,
             align=PP_ALIGN.LEFT):
        box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        frame = box.text_frame
        frame.word_wrap = True
        for index, line in enumerate(value.split("\n")):
            paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
            paragraph.alignment = align
            run = paragraph.add_run()
            run.text = line
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.color.rgb = colour
            run.font.name = "Helvetica"
        return box

    def heading(slide, title, subtitle=None):
        text(slide, 0.7, 0.45, 12, 0.7, title, size=30, bold=True, colour=ink)
        if subtitle:
            text(slide, 0.7, 1.12, 11.9, 0.6, subtitle, size=14, colour=muted)

    def note(slide, value, top=6.9):
        text(slide, 0.7, top, 12, 0.4, value, size=10, colour=muted)

    def style_header(cell, size=12):
        cell.fill.solid()
        cell.fill.fore_color.rgb = navy
        for paragraph in cell.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(size)
                run.font.bold = True
                run.font.color.rgb = white

    def style_body(cell, size=11, bold=False, align=None):
        for paragraph in cell.text_frame.paragraphs:
            if align is not None:
                paragraph.alignment = align
            for run in paragraph.runs:
                run.font.size = Pt(size)
                run.font.bold = bold
                run.font.color.rgb = ink

    headline = key["headline"]
    bridge = key["bridge"]
    gap = bridge["total"]

    # 1 - cover
    cover = prs.slides.add_slide(blank)
    fill = cover.background.fill
    fill.solid()
    fill.fore_color.rgb = navy
    text(cover, 0.9, 2.1, 11.5, 0.8, "Monthly management pack", size=44, bold=True, colour=white)
    text(cover, 0.9, 3.05, 11.5, 0.7, f"{key['month']}", size=32, colour=RGBColor(198, 220, 232))
    text(
        cover, 0.9, 3.95, 11.5, 0.6,
        f"Gross profit {money.grouped(gap)} KES against budget "
        f"({headline['gross_profit_variance_pct']}%)",
        size=18, colour=white,
    )
    text(
        cover, 0.9, 5.9, 11.5, 0.8,
        f"Synthetic ledger, fingerprint {key['fingerprint']}  |  "
        f"{len(key['lines'])} lines, 3 branches, 18 months  |  17 published checks",
        size=11, colour=RGBColor(198, 220, 232),
    )

    # 2 - headline
    slide = prs.slides.add_slide(blank)
    heading(slide, "The headline", "One month, two numbers, and the driver behind them")
    for index, (value, label, colour) in enumerate(
        (
            (money.grouped(gap), "gross profit variance (KES)", warn),
            (f"{headline['gross_profit_variance_pct']}%", "gross profit vs budget", warn),
            (f"{headline['revenue_variance_pct']}%", "revenue vs budget", ink),
        )
    ):
        left = 0.7 + index * 4.1
        shape = slide.shapes.add_shape(1, Inches(left), Inches(2.0), Inches(3.7), Inches(1.7))
        shape.fill.solid()
        shape.fill.fore_color.rgb = light
        shape.line.color.rgb = RGBColor(214, 222, 230)
        text(slide, left + 0.15, 2.25, 3.4, 0.8, value, size=30, bold=True, colour=colour,
             align=PP_ALIGN.LEFT)
        text(slide, left + 0.15, 3.1, 3.4, 0.5, label, size=12, colour=muted)
    text(
        slide, 0.7, 4.3, 12, 1.2,
        f"Revenue is roughly on plan; gross profit is not. {headline['largest_driver'].capitalize()} "
        f"is the largest single driver of the gap, and every figure on the following slides "
        f"reconciles to it.",
        size=18, colour=ink,
    )
    note(slide, "All figures from outputs/answer_key.json; synthetic ledger, disclosed.")

    # 3 - bridge chart
    slide = prs.slides.add_slide(blank)
    heading(slide, "Where the profit went", "Budget to actual, four drivers that sum to the gap")
    slide.shapes.add_picture(
        str(CHARTS / "01_bridge_waterfall.png"), Inches(0.7), Inches(1.7),
        width=Inches(11.9),
    )
    note(slide, "Each bar carries its value and its share of the gap; axis starts near the level, not at zero.")

    # 4 - driver table
    slide = prs.slides.add_slide(blank)
    heading(slide, "Price and cost did the damage", "The bridge in numbers")
    table = slide.shapes.add_table(
        6, 3, Inches(0.7), Inches(1.8), Inches(11.9), Inches(3.9)
    ).table
    table.columns[0].width = Inches(6.4)
    table.columns[1].width = Inches(2.7)
    table.columns[2].width = Inches(2.8)
    for column, label in enumerate(("Driver", "KES", "Share of budget GP")):
        cell = table.cell(0, column)
        cell.text = label
        style_header(cell, size=13)
    budget_gp = Decimal(bridge["budget_gross_profit"])
    for row_index, (name, label) in enumerate(
        (
            ("volume", "Volume - total units at budget margin"),
            ("mix", "Mix - a different blend at budget margins"),
            ("price", "Price - actual units at the change in selling price"),
            ("cost", "Cost - actual units at the change in unit cost"),
        ),
        start=1,
    ):
        value = Decimal(bridge[name])
        values = (label, money.grouped(value), f"{money.cents(value / budget_gp * 100)}%")
        for column, value_text in enumerate(values):
            cell = table.cell(row_index, column)
            cell.text = value_text
            style_body(cell, size=12, align=PP_ALIGN.RIGHT if column else PP_ALIGN.LEFT)
    total = ("Total variance", money.grouped(gap),
             f"{money.cents(Decimal(gap) / budget_gp * 100)}%")
    for column, value_text in enumerate(total):
        cell = table.cell(5, column)
        cell.text = value_text
        style_body(cell, size=12, bold=True, align=PP_ALIGN.RIGHT if column else PP_ALIGN.LEFT)
    note(slide, "The four rows add to the total to the cent.")

    # 5 - owners
    slide = prs.slides.add_slide(blank)
    heading(slide, "Who owns it", "Each driver attributed to the department that can act on it")
    slide.shapes.add_picture(
        str(CHARTS / "03_variance_by_owner.png"), Inches(0.7), Inches(1.75),
        width=Inches(8.0),
    )
    owners = slide.shapes.add_table(
        5, 3, Inches(8.6), Inches(1.9), Inches(4.1), Inches(2.6)
    ).table
    owners.columns[0].width = Inches(2.3)
    owners.columns[1].width = Inches(1.1)
    owners.columns[2].width = Inches(0.7)
    for column, label in enumerate(("Department", "KES", "Share")):
        cell = owners.cell(0, column)
        cell.text = label
        style_header(cell, size=9)
    for index, (name, value, share) in enumerate(_owner_rows(key), start=1):
        for column, value_text in enumerate((name, value, share)):
            cell = owners.cell(index, column)
            cell.text = value_text
            style_body(cell, size=9, align=PP_ALIGN.RIGHT if column else PP_ALIGN.LEFT)
    note(slide, "Ownership is arithmetic: the department that can move the largest component of each line.")

    # 6 - line level
    slide = prs.slides.add_slide(blank)
    heading(slide, "Line level", "The five worst lines, each with its owner")
    table = slide.shapes.add_table(
        6, 6, Inches(0.7), Inches(1.8), Inches(11.9), Inches(3.6)
    ).table
    widths = (2.0, 3.3, 1.7, 1.6, 1.7, 2.2)
    for index, width in enumerate(widths):
        table.columns[index].width = Inches(width)
    for column, label in enumerate(("Branch", "Product", "Variance", "Price", "Unit cost", "Owner")):
        cell = table.cell(0, column)
        cell.text = label
        style_header(cell, size=12)
    for row_index, row in enumerate(key["lines"][:5], start=1):
        values = (
            row["branch"], row["product"], money.grouped(row["variance"]),
            money.grouped(row["price"]), money.grouped(row["cost_rate"]), row["owner"],
        )
        for column, value_text in enumerate(values):
            cell = table.cell(row_index, column)
            cell.text = value_text
            style_body(
                cell, size=11,
                align=PP_ALIGN.RIGHT if column in (2, 3, 4) else PP_ALIGN.LEFT,
            )
    note(slide, f"All {len(key['lines'])} lines are in outputs/tables/line_variance.csv.")

    # 7 - actions
    slide = prs.slides.add_slide(blank)
    heading(slide, "What I would do first", "Owner, action, value at stake")
    top = 1.75
    for row in _actions(key):
        text(slide, 0.7, top, 2.9, 0.9, row["owner"], size=15, bold=True, colour=navy)
        text(
            slide, 3.7, top, 6.9, 1.0,
            f"{row['action']}  ({row['finding']})",
            size=11, colour=ink,
        )
        text(
            slide, 10.8, top, 1.9, 0.6,
            money.grouped(abs(Decimal(row["gross_profit_impact"]))),
            size=14, bold=True, colour=warn, align=PP_ALIGN.RIGHT,
        )
        top += 1.15
    note(slide, "Worth of gross profit, review date the last working day of next month.")

    # 8 - method
    slide = prs.slides.add_slide(blank)
    heading(slide, "Method, limits, and how to regenerate", "What a reader should not have to take on trust")
    bullets = [
        "Flexed budget: actual volume at budget price and cost. Volume, mix, price and cost "
        "reconcile to the cent.",
        "Mix is the residual of the volume movement, so it is a portfolio effect - no single "
        "product manager owns it.",
        "Gross profit only: no overhead allocation, no tax, no FX, no write-offs.",
        f"{len(key['lines'])} lines, 3 branches, 18 months, 17 published checks over 16 distinct identities.",
        "Synthetic seeded ledger; a hand-edited line fails its fingerprint check.",
        "Regenerate the pack with make run; rebuild this deck and the PDF with make docs.",
    ]
    text(slide, 0.7, 1.9, 12, 4.4, "\n\n".join(f"- {line}" for line in bullets), size=15, colour=ink)
    note(slide, "How a pack like this runs month to month: docs/how-a-management-pack-is-produced.md")

    core = prs.core_properties
    core.author = "Sting Analytics"
    core.title = f"Monthly management pack - {key['month']}"
    core.subject = "Synthetic management reporting pack"
    core.created = dt.datetime(2026, 6, 30, 12, 0, 0)
    core.modified = dt.datetime(2026, 6, 30, 12, 0, 0)
    core.last_modified_by = "Sting Analytics"
    core.revision = 1
    prs.save(str(path))
    _normalise_zip(path)
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--month", default=MONTH, help=f"month to publish (default: {MONTH})")
    parser.add_argument("--out", default=str(ROOT / "docs"), help="directory to write into")
    args = parser.parse_args(argv)

    if args.month not in MONTHS:
        raise KeyError(f"{args.month} is not in this ledger")

    ledger = Ledger.from_dict(generator.build_ledger())
    analysis = analyse_month(ledger, args.month)
    answer_key = key_mod.build_answer_key(ledger, args.month)
    directory = Path(args.out)
    directory.mkdir(parents=True, exist_ok=True)

    report = directory / f"report-{args.month}.md"
    brief = directory / "how-a-management-pack-is-produced.md"
    pdf = directory / f"monthly-pack-{args.month}.pdf"
    deck = directory / f"monthly-pack-{args.month}.pptx"

    report.write_text(report_markdown(analysis, answer_key), encoding="utf-8")
    brief.write_text(brief_markdown(answer_key), encoding="utf-8")
    build_pdf(analysis, answer_key, pdf)
    build_pptx(analysis, answer_key, deck)

    for path in (report, brief, pdf, deck):
        print(f"wrote  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
