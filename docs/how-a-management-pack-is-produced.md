# How a monthly management pack is produced

A management pack is not a dashboard and not a set of accounts. It is the one document a leadership team reads to decide what to change this month, and it is judged by whether it answers three questions: **what moved, what caused it, and who is going to do something about it.** This is the cycle behind the pack in this repository, written the way it runs in a trading business.

## 1. Days 1-2: close and lock the data

- Sales and margin are cut from the transaction system, purchases from the purchase ledger, and both are tied back to the general ledger control accounts before anything is analysed. An unreconciled close makes every later number arguable.
- The budget register is frozen for the year. If the plan is re-phased in the analysis, the variance stops being a performance measure and becomes a negotiation.
- The dataset is fingerprinted. Here a SHA-256 over the canonical ledger stands in for the month-end lock: a hand-edited line no longer matches its fingerprint and the published checks fail.

## 2. Day 2: flex the budget before judging anyone

Comparing actual gross profit with a fixed budget confuses three different failures. The flexed budget - actual volume at budget price and budget cost - splits the movement cleanly:

- **Volume** is total units at the budget's gross profit per unit.
- **Mix** is what is left of the volume movement once total units are removed: the effect of selling a different blend.
- **Price** is actual units at the change in selling price, so a discount shows up even on a line that sold exactly to plan.
- **Cost** is actual units at the change in unit cost, which is what separates supplier inflation from a branch that cannot sell.

The four components are defined to sum to the total to the cent. That identity is the control: if they do not reconcile, the decomposition is wrong, not approximately right.

## 3. Day 3: decompose to the line, then assign an owner

A portfolio-level bridge tells the board what happened; it does not tell anyone what to do. The pack therefore decomposes every product line in every branch and attributes each one - 120 lines here - to the department that can move its largest component: Commercial / Pricing for price, Procurement for cost, Branch Sales for volume. Mix stays at portfolio level, because no single product manager owns the blend.

Ownership is assigned by arithmetic, not by opinion, which is what makes it defensible in the meeting: the rule is published, so an owner can argue with the numbers but not with the method.

## 4. Day 3: escalate only what is material

A pack that lists everything gets read as noise. Exceptions are selected by threshold and ranked by gross-profit impact:

- Materiality: **10,000.00 KES** of gross profit.
- Price erosion: realised price below **97.5%** of the budgeted price on the volume actually sold.
- Cost step: unit cost above **102.5%** of budget on the volume bought.
- Branch trend: below budget on units in **at least 2 of the last 3 months**, with a rolling gap of **5%** or more. Reading units rather than profit matters - a branch discounting its way to a miss has a pricing problem, not a trading one.

This month that produces 4 exceptions, and Mombasa Road is the branch off track.

## 5. Day 4: write the pack in reading order

1. **The headline** - two lines: what the result was, and how far off plan.
2. **The bridge** - where the gap came from, in four components that reconcile.
3. **Where it sits** - branch, category and the worst lines, with names attached.
4. **The actions** - owner, action, value at stake, review date. No action without an owner; no owner without a date.

Every figure in the narrative is generated from the same answer key as the tables, so the prose cannot drift from the numbers. The charts carry their own labels for the same reason: a reader should not need the table to understand the picture.

## 6. Day 4-5: the meeting, then the register

The pack exists to be argued with in a 45-minute meeting with three outputs: the two or three actions that get funded, the owner and date for each, and anything that needs a decision above the meeting's authority. Last month's actions are the first item on the agenda, not the last - otherwise the pack becomes a monthly description of the same problem.

## 7. Controls a reader should expect

- The bridge reconciles to the cent, and the line table reconciles to the bridge.
- Budget and actuals cover exactly the same lines; a missing line is a failure, not a zero.
- The answer key is checked against a recomputation, not against itself.
- Every published figure is reproducible from the ledger with one command. Here that is `make run`, and the seventeen checks are published rather than asserted.

## 8. What this repository automates, and what it does not

Automated: the ledger, the flex, the bridge, the decomposition, ownership, exception selection, the tables, the charts, the validation report, this brief's figures, and the PDF and slide exports.

Not automated, and deliberately so: deciding whether a price move was a mistake or a strategy, judging whether a cost step is temporary, choosing which actions to fund, and fixing the data-quality problems that a close always finds. A pack that pretends to decide those things is a pack nobody trusts.

## 9. This month, in one line

Gross profit missed budget by KES 73,405.91 (-19.38%); price is the largest driver and Branch Sales owns the first action. Read the [report](report-2026-06.md), the [PDF](monthly-pack-2026-06.pdf) or the [deck](monthly-pack-2026-06.pptx).
