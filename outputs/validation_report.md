# Validation report

**17/17 checks pass, covering sixteen distinct identities.** The full bridge identity is the sum of its two halves, so it corroborates them rather than counting as a separate property. Each check compares a published figure against an identity it was not derived from.

| Check | Outcome | Detail |
|---|---|---|
| ledger covers every month, branch and sku | pass | 2160 budget and 2160 actual lines, 2160 expected |
| catalogue holds four categories of ten skus | pass | 40 skus: {'Home Care': 10, 'Beverages': 10, 'Staples': 10, 'Snacks': 10} |
| budget price is constant within a year | pass | 80 year-and-sku combinations, one price each |
| unit cost stays below the selling price | pass | 0 lines with cost at or above price |
| fingerprint matches the canonical ledger | pass | published f8b8fa811c7ef11b, recomputed f8b8fa811c7ef11b |
| budget and actuals cover identical lines | pass | 120 keys, 0 mismatched |
| bridge components sum to the total variance | pass | -73,405.91 against -73,405.91 |
| flexed budget equals actual volume at budget rates | pass | 373,335.76 recomputed, 373,335.76 published |
| flexed less budget equals volume plus mix | pass | -5,408.74 against -5,408.74 |
| actual less flexed equals price plus cost | pass | -67,997.17 against -67,997.17 |
| mix is zero when every product scales together | pass | mix 0.00, volume 4,000.00 on a doubling of every product |
| branch variances sum to actual gross profit | pass | 305,338.59 against 305,338.59 |
| category variances sum to actual gross profit | pass | 305,338.59 against 305,338.59 |
| exception list is sorted by impact | pass | 4 exceptions, largest 41,382.41 |
| unit-cost drift sums to the bridge cost | pass | -26,053.41 across 120 lines, bridge -26,053.41 |
| line variances sum to the bridge total | pass | -73,405.91 across 120 lines, bridge -73,405.91 |
| answer key matches recomputed bridge | pass | key total -73,405.91, recomputed -73,405.91 |
