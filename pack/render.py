"""Markdown rendering for the monthly pack and the answer key.

Rendering is a pure function of the analysis and the answer key: nothing here
writes a file, so the same text can be tested without touching disk.
"""

from decimal import Decimal

from . import money, variance


def monthly_pack(analysis: variance.MonthAnalysis, key: dict) -> str:
    headline = key["headline"]
    bridge = key["bridge"]
    revenue_gap = Decimal(headline["revenue_variance_pct"])
    profit_gap = Decimal(headline["gross_profit_variance_pct"])
    variance_total = Decimal(headline["gross_profit_variance"])

    lines = [
        f"# Monthly management pack — {analysis.month}",
        "",
        (
            "> **Synthetic data.** Every figure below is generated from a seeded, "
            f"documented mechanism (ledger fingerprint `{key['fingerprint']}`). "
            "No client figures appear in this pack."
        ),
        "",
        "## Headline",
        "",
        "| | Budget | Actual | Variance | Variance % |",
        "|---|---:|---:|---:|---:|",
        (
            f"| Revenue | {money.grouped(headline['revenue_budget'])} | "
            f"{money.grouped(headline['revenue_actual'])} | "
            f"{money.grouped(headline['revenue_variance'])} | "
            f"{revenue_gap}% |"
        ),
        (
            f"| Gross profit | {money.grouped(headline['gross_profit_budget'])} | "
            f"{money.grouped(headline['gross_profit_actual'])} | "
            f"{money.grouped(headline['gross_profit_variance'])} | "
            f"{profit_gap}% |"
        ),
        "",
        (
            f"Revenue came in {abs(revenue_gap)}% off budget; gross profit came in "
            f"{abs(profit_gap)}% off it, a shortfall of "
            f"KES {money.grouped(abs(variance_total))}. The gap between those two "
            "percentages is the whole story of the month: the business sold roughly "
            "the volume it planned and kept far less of the money."
        ),
        "",
        "## The bridge",
        "",
        "| Driver | KES | Share of budget gross profit |",
        "|---|---:|---:|",
    ]

    budget_gp = Decimal(bridge["budget_gross_profit"])
    for name, label in (
        ("volume", "Volume — total units at budget margin per unit"),
        ("mix", "Mix — selling a different blend at budget margins"),
        ("price", "Price — actual units at the change in selling price"),
        ("cost", "Cost — actual units at the change in unit cost"),
    ):
        value = Decimal(bridge[name])
        share = money.cents(value / budget_gp * 100) if budget_gp else Decimal("0.00")
        lines.append(f"| {label} | {money.grouped(value)} | {share}% |")
    lines.append(
        f"| **Total variance** | **{money.grouped(Decimal(bridge['total']))}** | |"
    )
    lines.append("")
    lines.append(
        "Reconciliation: "
        f"{money.grouped(bridge['volume'])} + {money.grouped(bridge['mix'])} + "
        f"{money.grouped(bridge['price'])} + {money.grouped(bridge['cost'])} = "
        f"{money.grouped(bridge['total'])}, which equals actual gross profit less "
        "budget gross profit to the cent. The flexed budget — actual volume at "
        f"budget price and cost — is {money.grouped(bridge['flexed_gross_profit'])}: "
        "volume plus mix accounts for the difference between budget and flex, "
        "price plus cost for the difference between flex and actual."
    )
    lines.append("")

    lines += [
        "## Exceptions",
        "",
        f"Lines at or beyond the materiality threshold of "
        f"KES {money.grouped(key['materiality'])}.",
        "",
        "| Line | Finding | Driver | Impact (KES) | Owner | Action |",
        "|---|---|---|---:|---|---|",
    ]
    for row in key["exceptions"]:
        lines.append(
            f"| {row['label']} | {row['finding']} | {row['driver']} | "
            f"{money.grouped(row['gross_profit_impact'])} | {row['owner']} | "
            f"{row['action']} |"
        )
    lines.append("")

    lines += [
        "## Where it sits",
        "",
        "### By branch",
        "",
        "| Branch | Budget GP | Actual GP | Variance | % |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in key["by_branch"]:
        lines.append(
            f"| {row['branch']} | {money.grouped(row['budget_gross_profit'])} | "
            f"{money.grouped(row['actual_gross_profit'])} | "
            f"{money.grouped(row['variance'])} | {row['variance_pct']}% |"
        )
    lines += [
        "",
        "### By category",
        "",
        "| Category | Budget GP | Actual GP | Variance | % |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in key["by_category"]:
        lines.append(
            f"| {row['category']} | {money.grouped(row['budget_gross_profit'])} | "
            f"{money.grouped(row['actual_gross_profit'])} | "
            f"{money.grouped(row['variance'])} | {row['variance_pct']}% |"
        )
    lines.append("")

    lines += [
        "### By line — the five worst",
        "",
        "| Branch | Product | Variance | Price | Unit cost | Volume | Owner |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in key["lines"][:5]:
        volume = Decimal(row["volume_revenue"]) + Decimal(row["volume_cost"])
        lines.append(
            f"| {row['branch']} | {row['product']} | "
            f"{money.grouped(row['variance'])} | {money.grouped(row['price'])} | "
            f"{money.grouped(row['cost_rate'])} | {money.grouped(volume)} | "
            f"{row['owner']} |"
        )
    lines.append("")

    lines += ["## What I would do first", ""]
    for index, row in enumerate(key["exceptions"][:3], start=1):
        lines.append(
            f"{index}. **{row['owner']}** — {row['action']}. "
            f"Worth KES {money.grouped(abs(Decimal(row['gross_profit_impact'])))} "
            f"of gross profit, review date the last working day of next month."
        )
    lines += [
        "",
        "## Method and limits",
        "",
        "- Budget is set once per calendar year; the actuals drift from it through "
        "four documented mechanisms plus seeded noise.",
        "- Mix is the part of the volume movement not explained by total units, so "
        "the four components reconcile exactly rather than approximately.",
        "- Single currency (KES), no tax, no foreign exchange, no write-offs, no "
        "allocation of overhead. This is a gross-profit pack, not a P&L.",
        "- Regenerate with `make run`; the ledger fingerprint proves the run.",
        "",
    ]
    return "\n".join(lines)


def answer_key_md(key: dict) -> str:
    headline = key["headline"]
    bridge = key["bridge"]
    lines = [
        f"# Answer key — {key['month']}",
        "",
        f"Ledger fingerprint `{key['fingerprint']}` (seed {key['seed']}). "
        "Synthetic data, disclosed.",
        "",
        "## Headline",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Revenue — budget | {money.grouped(headline['revenue_budget'])} |",
        f"| Revenue — actual | {money.grouped(headline['revenue_actual'])} |",
        f"| Revenue — variance | {headline['revenue_variance_pct']}% |",
        f"| Gross profit — budget | {money.grouped(headline['gross_profit_budget'])} |",
        f"| Gross profit — actual | {money.grouped(headline['gross_profit_actual'])} |",
        f"| Gross profit — variance | {money.grouped(headline['gross_profit_variance'])} "
        f"({headline['gross_profit_variance_pct']}%) |",
        f"| Largest driver | {headline['largest_driver']} |",
        "",
        "## Bridge",
        "",
        "| Component | KES |",
        "|---|---:|",
    ]
    for name in (
        "budget_gross_profit",
        "volume",
        "mix",
        "price",
        "cost",
        "actual_gross_profit",
    ):
        if name == "actual_gross_profit":
            value = Decimal(bridge["budget_gross_profit"]) + Decimal(bridge["total"])
            lines.append(f"| **Actual gross profit** | **{money.grouped(value)}** |")
            continue
        lines.append(
            f"| {name.replace('_', ' ').capitalize()} | {money.grouped(bridge[name])} |"
        )
    lines.append(
        f"| **Total variance** | **{money.grouped(Decimal(bridge['total']))}** |"
    )
    lines += ["", "## Owners", "", "| Owner | Variance (KES) |", "|---|---:|"]
    for owner, value in key["owners"].items():
        lines.append(f"| {owner} | {money.grouped(value)} |")
    lines += ["", "## Exceptions", ""]
    for row in key["exceptions"]:
        lines.append(
            f"- **{row['label']}** ({row['driver']}, "
            f"KES {money.grouped(row['gross_profit_impact'])}) — {row['finding']} "
            f"*Owner: {row['owner']}.*"
        )
    lines.append("")
    return "\n".join(lines)
