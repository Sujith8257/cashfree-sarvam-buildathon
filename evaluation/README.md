# Does the ranked notebook preview find more paying loans?

From the repository root, run:

```sh
python -m evaluation.scorecard --k 3
```

**On this synthetic book, the preview finds one more paying loan at K=3 but selects INR 200 less in confirmed payments.** At K=1 it loses on both measures. These are observations about the selected loans, not money recovered by making calls.

```text
Synthetic notebook replay | seven-day horizon
Window: (2026-11-21T12:00:00+05:30, 2026-11-28T12:00:00+05:30]
Rows: 8 | eligible: 6 | requested K: 3 | selected: 3
Order      Hits   Precision   Confirmed INR   Selected loan IDs
Preview    2      66.7%       1,000.00        L006, L004, L005
Loan ID    1      33.3%       1,200.00        L001, L002, L003
Swap name: 0/28 orders changed; 1 eligible equal-date pair(s) tested.
Swap language: 0/28 orders changed; 1 eligible equal-date pair(s) tested.
Swap name+language: 0/28 orders changed; 1 eligible equal-date pair(s) tested.
Observed synthetic payments only; no causal effect or demographic fairness inferred.
```

### All budgets on this book

Each entry is **distinct paying loans / confirmed INR**. Both methods use the same K and the same six eligible IDs. Precision is hits divided by the number actually selected. K above six selects all six; K=0 selects none and precision is undefined (`null` in JSON).

| K | Ranked preview | Loan-ID order |
|---:|---:|---:|
| 1 | 0 / 0 | 1 / 1,200 |
| 2 | 1 / 650 | 1 / 1,200 |
| 3 | 2 / 1,000 | 1 / 1,200 |
| 4 | 2 / 1,000 | 2 / 1,850 |
| 5 | 2 / 1,000 | 3 / 2,200 |
| 6 or more | 3 / 2,200 | 3 / 2,200 |

### What is actually measured?

1. **Freeze the decision.** [book.json](book.json) contains eight invented OCR rows at noon IST on 21 November 2026. Only the six declared snapshot fields are accepted. Each `customer_id` represents one synthetic loan with one installment; missing or duplicate IDs are rejected. The evaluator posts these rows through the app's actual `POST /trigger/notebook` handler using `dry_run=true` and reads its `call_queue` in order. The baseline sorts exactly those IDs lexicographically. `L007` has zero outstanding; `L008` is not due yet.
2. **Check the full order before opening the labels.** For each of the 28 pairs of notebook rows, replay the endpoint three times: swap only names, only written language values, then both. IDs, row positions and all financial fields stay fixed. Compare the entire ordered list of eligible IDs, including loans below K and any change in eligibility. The two earliest loans share 10 November as their due date: `L006` precedes `L004` on the page even though its name and ID sort later. A changed order is reported with a witness pair and makes the CLI exit nonzero.
3. **Unblind and score.** Only after both orders are frozen and all replays finish does the evaluator open [withheld_outcomes.json](withheld_outcomes.json). A hit is a selected loan with at least one positive synthetic **confirmed** payment strictly after the snapshot and up to and including noon IST on 28 November. Sum incremental event amounts in integer paise, not outstanding balances or claims. `L004` has two partial payments totaling INR 650 and counts as one hit. `L006` has a claim and a confirmation one second too late; neither counts. Missing eligible-loan follow-up, an incomplete observation window, or duplicate eligible-ledger event IDs fail the run. An explicit `[]` means observed with no payments.

The fixtures were hand-authored separately from the existing ranker to exercise edge cases. “Held out” means future outcomes are withheld from ranking; it does **not** mean a blinded population sample or a statistically validated model. No borrower was contacted. Both orders are scored on the same undisturbed outcomes; there is no treatment group, causal uplift estimate, or evidence of real-world accuracy. Passing these swaps only establishes order invariance for these fields on this book. It does not establish demographic fairness, absence of proxy effects, or how OCR handles different scripts.

### Reproduce or integrate

```sh
python -m evaluation.scorecard --k 1        # losing example
python -m evaluation.scorecard --k 99       # budget capped to available loans
python -m evaluation.scorecard --k 3 --json # exact IDs, paise, audit differences
python -m pytest -q evaluation/test_scorecard.py
python -m pytest -q
```

Requires the PR #2 notebook preview (`d1498ed`, also present in PR #3) and the repository's existing [Python dependencies](../calltrigger-api/requirements.txt), including `httpx` for the in-process FastAPI `TestClient`. No additional package, key, database setup or running server is needed. The harness supplies only OCR output and a fixed clock, disables dotenv loading and outbound `requests` HTTP, and uses fresh in-memory dispatch state and a temporary `COLLECTIONS_DB` for every replay. This is a post-OCR evaluation; it does not exercise a live OCR, payment, or calling provider.
