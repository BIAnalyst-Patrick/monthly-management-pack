# Monthly management pack — 2026-06

> **Synthetic data.** Every figure below is generated from a seeded, documented mechanism (ledger fingerprint `f8b8fa811c7ef11b`). No client figures appear in this pack.

## Headline

| | Budget | Actual | Variance | Variance % |
|---|---:|---:|---:|---:|
| Revenue | 1,463,426.72 | 1,452,532.75 | -10,893.97 | -0.74% |
| Gross profit | 378,744.50 | 305,338.59 | -73,405.91 | -19.38% |

Revenue came in 0.74% off budget; gross profit came in 19.38% off it, a shortfall of KES 73,405.91. The gap between those two percentages is the whole story of the month: the business sold roughly the volume it planned and kept far less of the money.

## The bridge

| Driver | KES | Share of budget gross profit |
|---|---:|---:|
| Volume — total units at budget margin per unit | 8,755.42 | 2.31% |
| Mix — selling a different blend at budget margins | -14,164.16 | -3.74% |
| Price — actual units at the change in selling price | -41,943.76 | -11.07% |
| Cost — actual units at the change in unit cost | -26,053.41 | -6.88% |
| **Total variance** | **-73,405.91** | |

Reconciliation: 8,755.42 + -14,164.16 + -41,943.76 + -26,053.41 = -73,405.91, which equals actual gross profit less budget gross profit to the cent. The flexed budget — actual volume at budget price and cost — is 373,335.76: volume plus mix accounts for the difference between budget and flex, price plus cost for the difference between flex and actual.

## Exceptions

Lines at or beyond the materiality threshold of KES 10,000.00.

| Line | Finding | Driver | Impact (KES) | Owner | Action |
|---|---|---|---:|---|---|
| Mombasa Road (3 months) | Units below budget in 3 of the last 3 months, 10.86% down on a rolling basis: this is a branch drifting, not one bad month, and the unit gap is worth KES 41,382.41 of gross profit at budget margins. | volume | -41,382.41 | Branch Sales | Rebuild the Mombasa Road trading plan against the trend gap |
| Nakuru | Prices realised 9.87% below the budgeted price for the volume actually sold, costing KES 40,901.06 of gross profit on KES 379,260.56 of budgeted branch revenue. | price | -40,901.06 | Commercial / Pricing | Reissue the Nakuru price file and cap discount authority at 7% |
| Home Care | Unit costs on Home Care are running 6.56% above budget on the volume bought, costing KES 25,934.14 of gross profit. | cost | -25,934.14 | Procurement | Renegotiate Home Care supply terms or reprice the range |
| Product mix | The blend moved towards lower-margin lines: Staples went from 25.00% of budgeted units to 31.56% actual, costing KES 14,164.16 of gross profit at budget margins. | mix | -14,164.16 | Category Management | Review Staples ranging, promo depth and shelf allocation against the budgeted blend |

## Where it sits

### By branch

| Branch | Budget GP | Actual GP | Variance | % |
|---|---:|---:|---:|---:|
| Mombasa Road | 122,698.84 | 95,653.57 | -27,045.27 | -22.04% |
| Nairobi CBD | 157,890.59 | 153,663.91 | -4,226.68 | -2.68% |
| Nakuru | 98,155.07 | 56,021.11 | -42,133.96 | -42.93% |

### By category

| Category | Budget GP | Actual GP | Variance | % |
|---|---:|---:|---:|---:|
| Beverages | 54,634.10 | 44,495.43 | -10,138.67 | -18.56% |
| Home Care | 184,454.04 | 130,681.65 | -53,772.39 | -29.15% |
| Snacks | 84,593.31 | 72,280.31 | -12,313.00 | -14.56% |
| Staples | 55,063.05 | 57,881.20 | 2,818.15 | 5.12% |

### By line — the five worst

| Branch | Product | Variance | Price | Unit cost | Volume | Owner |
|---|---|---:|---:|---:|---:|---|
| Nakuru | Fabric Softener 1L | -3,950.82 | -2,742.60 | -1,068.00 | -140.22 | Commercial / Pricing |
| Nakuru | Scouring Powder 500g | -3,527.86 | -2,428.80 | -970.75 | -128.31 | Commercial / Pricing |
| Mombasa Road | Fabric Softener 1L | -3,427.92 | 104.40 | -1,288.80 | -2,243.52 | Branch Sales |
| Mombasa Road | Scouring Powder 500g | -3,051.30 | -92.96 | -1,162.00 | -1,796.34 | Branch Sales |
| Nakuru | Air Freshener 300ml | -2,824.04 | -1,963.84 | -860.20 | 0.00 | Commercial / Pricing |

## What I would do first

1. **Branch Sales** — Rebuild the Mombasa Road trading plan against the trend gap. Worth KES 41,382.41 of gross profit, review date the last working day of next month.
2. **Commercial / Pricing** — Reissue the Nakuru price file and cap discount authority at 7%. Worth KES 40,901.06 of gross profit, review date the last working day of next month.
3. **Procurement** — Renegotiate Home Care supply terms or reprice the range. Worth KES 25,934.14 of gross profit, review date the last working day of next month.

## Method and limits

- Budget is set once per calendar year; the actuals drift from it through four documented mechanisms plus seeded noise.
- Mix is the part of the volume movement not explained by total units, so the four components reconcile exactly rather than approximately.
- Single currency (KES), no tax, no foreign exchange, no write-offs, no allocation of overhead. This is a gross-profit pack, not a P&L.
- Regenerate with `make run`; the ledger fingerprint proves the run.
