# Monthly management pack — 2025-12

> **Synthetic data.** Every figure below is generated from a seeded, documented mechanism (ledger fingerprint `f8b8fa811c7ef11b`). No client figures appear in this pack.

## Headline

| | Budget | Actual | Variance | Variance % |
|---|---:|---:|---:|---:|
| Revenue | 1,599,826.83 | 1,612,209.60 | 12,382.77 | 0.77% |
| Gross profit | 408,318.31 | 383,924.57 | -24,393.74 | -5.97% |

Revenue came in 0.77% off budget; gross profit came in 5.97% off it, a shortfall of KES 24,393.74. The gap between those two percentages is the whole story of the month: the business sold roughly the volume it planned and kept far less of the money.

## The bridge

| Driver | KES | Share of budget gross profit |
|---|---:|---:|
| Volume — total units at budget margin per unit | 10,174.96 | 2.49% |
| Mix — selling a different blend at budget margins | -9,583.10 | -2.35% |
| Price — actual units at the change in selling price | -24,173.92 | -5.92% |
| Cost — actual units at the change in unit cost | -811.68 | -0.20% |
| **Total variance** | **-24,393.74** | |

Reconciliation: 10,174.96 + -9,583.10 + -24,173.92 + -811.68 = -24,393.74, which equals actual gross profit less budget gross profit to the cent. The flexed budget — actual volume at budget price and cost — is 408,910.17: volume plus mix accounts for the difference between budget and flex, price plus cost for the difference between flex and actual.

## Exceptions

Lines at or beyond the materiality threshold of KES 10,000.00.

| Line | Finding | Driver | Impact (KES) | Owner | Action |
|---|---|---|---:|---|---|
| Nakuru | Prices realised 5.50% below the budgeted price for the volume actually sold, costing KES 24,030.93 of gross profit on KES 413,933.38 of budgeted branch revenue. | price | -24,030.93 | Commercial / Pricing | Reissue the Nakuru price file and cap discount authority at 7% |

## Where it sits

### By branch

| Branch | Budget GP | Actual GP | Variance | % |
|---|---:|---:|---:|---:|
| Mombasa Road | 132,656.01 | 123,868.82 | -8,787.19 | -6.62% |
| Nairobi CBD | 170,015.58 | 174,415.83 | 4,400.25 | 2.59% |
| Nakuru | 105,646.72 | 85,639.92 | -20,006.80 | -18.94% |

### By category

| Category | Budget GP | Actual GP | Variance | % |
|---|---:|---:|---:|---:|
| Beverages | 58,725.83 | 53,732.76 | -4,993.07 | -8.50% |
| Home Care | 199,401.68 | 182,903.38 | -16,498.30 | -8.27% |
| Snacks | 91,589.62 | 84,861.50 | -6,728.12 | -7.35% |
| Staples | 58,601.18 | 62,426.93 | 3,825.75 | 6.53% |

### By line — the five worst

| Branch | Product | Variance | Price | Unit cost | Volume | Owner |
|---|---|---:|---:|---:|---:|---|
| Nakuru | Fabric Softener 1L | -1,852.37 | -1,570.80 | -148.24 | -133.33 | Commercial / Pricing |
| Nakuru | Toilet Cleaner 750ml | -1,275.33 | -1,173.00 | -213.00 | 110.67 | Commercial / Pricing |
| Nakuru | Air Freshener 300ml | -1,201.98 | -1,139.97 | -62.01 | 0.00 | Commercial / Pricing |
| Nakuru | Scouring Powder 500g | -1,200.08 | -1,577.40 | 133.32 | 244.00 | Commercial / Pricing |
| Nairobi CBD | Lentils 1kg | 1,069.17 | 32.40 | 68.85 | 967.92 | Branch Sales |

## What I would do first

1. **Commercial / Pricing** — Reissue the Nakuru price file and cap discount authority at 7%. Worth KES 24,030.93 of gross profit, review date the last working day of next month.

## Method and limits

- Budget is set once per calendar year; the actuals drift from it through four documented mechanisms plus seeded noise.
- Mix is the part of the volume movement not explained by total units, so the four components reconcile exactly rather than approximately.
- Single currency (KES), no tax, no foreign exchange, no write-offs, no allocation of overhead. This is a gross-profit pack, not a P&L.
- Regenerate with `make run`; the ledger fingerprint proves the run.
