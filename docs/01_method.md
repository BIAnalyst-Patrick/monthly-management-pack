# Method

## Notation

For product `i` in a month:

| Symbol | Meaning |
|---|---|
| `Vb_i`, `Va_i` | budget and actual volume in units |
| `Pb_i`, `Pa_i` | budget and actual selling price per unit |
| `Cb_i`, `Ca_i` | budget and actual unit cost |
| `m_i = Pb_i - Cb_i` | budget gross profit per unit |

Gross profit is volume times unit margin:

```
GP_b = Σ Vb_i · m_i
GP_a = Σ Va_i · (Pa_i - Ca_i)
```

## The flexed budget

```
Flex = Σ Va_i · m_i
```

Actual volume, valued at the rates the budget was built on: budget price and
budget cost. This is the pivot of the whole analysis. Without it, the comparison
between budget and actual confuses "we sold a different amount" with "we bought
and charged differently", and the resulting number cannot be assigned to anyone.

## The four components

```
Volume = (Σ Va - Σ Vb) · (GP_b / Σ Vb)
Mix    = Σ (Va_i - Vb_i) · m_i  -  Volume
Price  = Σ Va_i · (Pa_i - Pb_i)
Cost   = Σ Va_i · (Cb_i - Ca_i)
```

`Volume` is total units moved, converted to money at the budget's gross profit
per unit. `Mix` is whatever is left of the volume-and-mix movement once the
total-volume effect is removed: it is the value, at budget margins, of selling a
different blend than planned.

## Why the identity holds

```
Volume + Mix
  = Σ (Va_i - Vb_i) · m_i                        (by definition of Mix as residual)
  = Flex - GP_b

Price + Cost
  = Σ Va_i · [(Pa_i - Pb_i) + (Cb_i - Ca_i)]
  = Σ Va_i · [(Pa_i - Ca_i) - (Pb_i - Cb_i)]
  = GP_a - Flex
```

Therefore:

```
Volume + Mix + Price + Cost = GP_a - GP_b
```

Exactly, with no residual term. Every component is computed in `Decimal` and
quantised to cents, and `Volume` is the one rounded figure; `Mix` absorbs the
rounding because it is derived as a residual. That is a deliberate choice: a
bridge that reconciles to the shilling is one an accountant can put in front of a
board, and the `Decimal` arithmetic means the equality is exact rather than
tolerant.

## Checks against degenerate cases

Two identities stop a plausible-looking wrong decomposition from passing:

- **Proportional scaling.** If every product's volume moves by the same factor,
  mix must be exactly zero. A decomposition that splits mix per product by simple
  subtraction fails this test.
- **Flat rates.** If every actual price and cost equals its budget, price and cost
  must both be exactly zero, and the entire variance must sit in volume and mix.

Both are asserted in `tests/test_variance.py` and re-checked independently in
`outputs/validation_report.md`.

## Attribution

| Component | Owner | Because |
|---|---|---|
| Volume | Branch Sales | units sold is a trading decision |
| Price | Commercial / Pricing | realised price is a pricing and discount-authority decision |
| Mix | Category Management | the blend sold is a ranging, promo and shelf decision |
| Cost | Procurement | unit cost is a buying decision |

The owner table is a partition: the four owner totals sum to the total variance,
which the validation report checks.

## Exceptions

A month produces findings, not a report card. Four rules run on the month's data:

| Rule | Trigger | Driver | Owner |
|---|---|---|---|
| Price erosion | realised price more than 2.5% below budget on the volume sold | price | Commercial / Pricing |
| Cost step | unit cost more than 2.5% above budget on the volume bought | cost | Procurement |
| Volume miss | units below 95% of budget for a branch | volume | Branch Sales |
| Blend shift | total mix effect at or beyond materiality | mix | Category Management |

Findings below **KES 10,000** of gross-profit impact are suppressed as immaterial
for a business of this size, and the remaining findings are sorted by absolute
impact so the first row is the first conversation. Each carries an owner and a
named action, because a variance with no owner is a fact rather than a decision.

## What this method cannot do

- It explains **gross profit**, not net profit: no overhead allocation, no
  distribution or marketing spend.
- It is a **single-period** decomposition. A multi-period bridge needs a price-
  and cost-volume revaluation at each month's rates, which this version does not do.
- It assumes a **fixed budget**. Re-forecasting, rolling plans and scenario
  modelling are out of scope, and the pack says so rather than implying otherwise.
