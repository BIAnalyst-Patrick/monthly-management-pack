"""Seeded generator for the budget and the actuals it drifts away from.

Four mechanisms are planted so that the diagnosis can be graded rather than
asserted: a discount creep, a mix shift, a supplier cost step, and a branch
volume shortfall. Everything else is small seeded noise.

The same seed always produces the same ledger, and the ledger carries a
fingerprint of its own canonical JSON so a reader can prove it.
"""

import hashlib
import json
import random
from decimal import Decimal

from .model import (
    BRANCHES,
    CATEGORIES,
    MONTHS,
    SEED,
    SKUS_PER_CATEGORY,
    to_money,
)

# Gross margin each category is built to earn, before anything drifts.
CATEGORY_MARGINS = {
    "Home Care": Decimal("0.30"),
    "Beverages": Decimal("0.22"),
    "Staples": Decimal("0.15"),
    "Snacks": Decimal("0.33"),
}

BRANCH_FACTORS = {
    "Nairobi CBD": Decimal("1.00"),
    "Nakuru": Decimal("0.62"),
    "Mombasa Road": Decimal("0.78"),
}

# Budget price points, roughly what an FMCG wholesaler would list.
CATEGORY_PRICE_BANDS = {
    "Home Care": (Decimal("180"), Decimal("520")),
    "Beverages": (Decimal("60"), Decimal("220")),
    "Staples": (Decimal("90"), Decimal("320")),
    "Snacks": (Decimal("50"), Decimal("240")),
}

PREFIX = {"Home Care": "HC", "Beverages": "BV", "Staples": "ST", "Snacks": "SN"}

PRODUCT_NAMES = {
    "Home Care": (
        "Washing Powder 1kg", "Dish Soap 500ml", "Bleach 1L",
        "Floor Cleaner 2L", "Laundry Bar 800g", "Toilet Cleaner 750ml",
        "Scouring Powder 500g", "Fabric Softener 1L", "Glass Cleaner 500ml",
        "Air Freshener 300ml",
    ),
    "Beverages": (
        "Bottled Water 1L", "Soda 500ml", "Juice 1L", "Energy Drink 330ml",
        "Tea Leaves 250g", "Coffee 200g", "Cordial 750ml", "Iced Tea 500ml",
        "Malted Drink 300ml", "Coconut Water 330ml",
    ),
    "Staples": (
        "Maize Flour 2kg", "Rice 5kg", "Cooking Oil 2L", "Sugar 2kg",
        "Wheat Flour 2kg", "Salt 1kg", "Beans 1kg", "Lentils 1kg",
        "Pasta 500g", "Porridge Mix 1kg",
    ),
    "Snacks": (
        "Biscuits 200g", "Crisps 100g", "Chocolate Bar 90g", "Peanuts 250g",
        "Cake 400g", "Cereal Bar 40g", "Popcorn 150g", "Sweets 200g",
        "Wafer 180g", "Nuts Mix 300g",
    ),
}

# Demand seasonality shared by budget and actuals: both know about December.
SEASONALITY = (
    Decimal("1.02"), Decimal("0.95"), Decimal("1.04"), Decimal("1.06"),
    Decimal("1.00"), Decimal("0.98"), Decimal("0.97"), Decimal("1.01"),
    Decimal("1.03"), Decimal("1.05"), Decimal("1.10"), Decimal("1.18"),
)

BUDGET_GROWTH_2026 = Decimal("1.06")
BUDGET_PRICE_INFLATION_2026 = Decimal("1.04")
BUDGET_COST_INFLATION_2026 = Decimal("1.035")

# The planted mechanisms, named so the README and the answer key can refer to
# them without duplicating numbers.
DISCOUNT_BRANCH = "Nakuru"          # branch-wide discounting, all categories
DISCOUNT_START = 4
DISCOUNT_PER_MONTH = Decimal("0.008")

MIX_CATEGORY = "Staples"          # lowest margin, and the one that grows
MIX_RIVAL_CATEGORY = "Home Care"  # highest-volume category, deliberately flat
MIX_START = 2
MIX_PER_MONTH = Decimal("1.022")

COST_CATEGORY = "Home Care"
COST_STEP_MONTH = 12              # 2026-01
COST_STEP = Decimal("1.065")

SHORT_BRANCH = "Mombasa Road"
SHORT_START = 7
SHORT_PER_MONTH = Decimal("0.978")

VOLUME_NOISE = 0.012
PRICE_NOISE = 0.004
COST_NOISE = 0.006


def fingerprint_of(payload) -> str:
    """Hash the canonical JSON of the ledger, excluding the fingerprint itself."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _catalogue():
    items = []
    for category in CATEGORIES:
        low, high = CATEGORY_PRICE_BANDS[category]
        span = high - low
        margin = CATEGORY_MARGINS[category]
        for index, name in enumerate(PRODUCT_NAMES[category]):
            price = to_money(low + span * Decimal(index) / Decimal(9))
            cost = to_money(price * (Decimal(1) - margin))
            items.append(
                {
                    "sku": f"{PREFIX[category]}-{index + 1:02d}",
                    "name": name,
                    "category": category,
                    "list_price": str(price),
                    "base_cost": str(cost),
                    "base_monthly_units": 45 + (index * 7) % 55,
                }
            )
    return items


def _month_factor(month: str) -> Decimal:
    return SEASONALITY[int(month[5:7]) - 1]


def _budget_line(item, branch, month) -> dict:
    year = int(month[:4])
    price = Decimal(item["list_price"])
    cost = Decimal(item["base_cost"])
    if year == 2026:
        price = to_money(price * BUDGET_PRICE_INFLATION_2026)
        cost = to_money(cost * BUDGET_COST_INFLATION_2026)

    volume = Decimal(item["base_monthly_units"]) * BRANCH_FACTORS[branch]
    volume *= _month_factor(month)
    if year == 2026:
        volume *= BUDGET_GROWTH_2026
    return {
        "month": month,
        "branch": branch,
        "sku": item["sku"],
        "volume": int(round(volume)),
        "price": str(price),
        "unit_cost": str(cost),
    }


def _category_drift(category: str, index: int) -> Decimal:
    """Staples (the lowest-margin category) grows; the rest hold flat."""
    if category == MIX_CATEGORY and index >= MIX_START:
        return MIX_PER_MONTH ** (index - MIX_START)
    return Decimal("1.000")


def _branch_drift(branch: str, index: int) -> Decimal:
    if branch == SHORT_BRANCH and index >= SHORT_START:
        return SHORT_PER_MONTH ** (index - SHORT_START)
    return Decimal("1.000")


def _price_drift(branch: str, category: str, index: int) -> Decimal:
    """The Nakuru branch discounts deeper every month it misses its number."""
    if branch == DISCOUNT_BRANCH and index >= DISCOUNT_START:
        return (Decimal(1) - DISCOUNT_PER_MONTH) ** (index - DISCOUNT_START)
    return Decimal("1.000")


def _cost_drift(category: str, index: int) -> Decimal:
    if category == COST_CATEGORY and index >= COST_STEP_MONTH:
        return COST_STEP
    return Decimal("1.000")


def _noise(rng, sigma: float) -> Decimal:
    return Decimal(str(max(0.90, 1.0 + rng.gauss(0.0, sigma))))


def build_ledger(seed: int = SEED) -> dict:
    """Build the whole ledger. Same seed, same numbers, every time."""
    rng = random.Random(seed)
    catalogue = _catalogue()
    index_of = {month: i for i, month in enumerate(MONTHS)}

    budgets, actuals = [], []
    for month in MONTHS:
        index = index_of[month]
        for branch in BRANCHES:
            for item in catalogue:
                budget = _budget_line(item, branch, month)
                budgets.append(budget)

                category = item["category"]
                volume = (
                    Decimal(budget["volume"])
                    * _category_drift(category, index)
                    * _branch_drift(branch, index)
                    * _noise(rng, VOLUME_NOISE)
                )
                price = (
                    Decimal(budget["price"])
                    * _price_drift(branch, category, index)
                    * _noise(rng, PRICE_NOISE)
                )
                cost = (
                    Decimal(budget["unit_cost"])
                    * _cost_drift(category, index)
                    * _noise(rng, COST_NOISE)
                )

                # Round the noisy factors to whole shillings so the ledger reads
                # like an export rather than a simulation.
                actuals.append(
                    {
                        "month": month,
                        "branch": branch,
                        "sku": item["sku"],
                        "volume": max(1, int(round(volume))),
                        "price": str(price.quantize(Decimal("0.01"))),
                        "unit_cost": str(cost.quantize(Decimal("0.01"))),
                    }
                )

    # Base demand drives the generator but is not part of the published ledger,
    # so a reader can recompute the fingerprint from what they are given.
    published_catalogue = [
        {k: v for k, v in item.items() if k != "base_monthly_units"}
        for item in catalogue
    ]

    payload = {
        "seed": seed,
        "months": list(MONTHS),
        "branches": list(BRANCHES),
        "catalogue": published_catalogue,
        "budgets": budgets,
        "actuals": actuals,
        "notes": [
            "Synthetic ledger generated from a documented, seeded mechanism.",
            "Budget is set once per calendar year; 2026 carries volume, price and cost inflation.",
            "Actuals drift from budget through four planted mechanisms and seeded noise.",
            "Single currency (KES), no tax, no foreign exchange, no write-offs.",
        ],
    }
    payload["fingerprint"] = fingerprint_of(payload)
    return payload


def write_ledger(path, seed: int = SEED) -> dict:
    ledger = build_ledger(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {k: v for k, v in ledger.items()}
    path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    return ledger
