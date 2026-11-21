# Who should Meena call next? — two-minute judge walkthrough

Use synthetic loan records, Cashfree **Test** mode, and only a consenting test phone. To run without calls or credentials, use the isolated [local walkthrough](lender-queue-demo.md) and replay the automated cases below. For a live payment, arrange the matching sandbox link and PG credentials first.

**Fastest offline rehearsal:** from the repository root run `python -m evaluation.rehearsal`. It drives the real FastAPI, signature verification, SQLite and ranking rules using a temporary database, synthetic clock and simulated provider HTTP responses. It prints the changing balance and queue; it never dials, charges or contacts a provider. Label this as a rehearsal when showing it.

| Time | What to show | Evidence to point at |
|---|---|---|
| 0:00–0:25 | In `/docs` (**Authorize** with `TRIGGER_API_KEY`), preview a notebook with `POST /trigger/notebook` and `dry_run=true`; read its `results`. | Only eligible rows enter `call_queue`. Every skipped row has a reason. A failed or incomplete scan doesn't start any calls. |
| 0:25–0:50 | In `/docs`, report a prior payment (`POST /queue/{iid}/already-paid`) or record hardship/no-contact (`POST /queue/{iid}/contact-preference`) on a synthetic borrower. | Their balance does not change. Outreach pauses, including across loans at the opted-out phone. [Contact stops](borrower-contact-preferences.md) |
| 0:50–1:15 | Record a dated [payment promise](promise-to-pay-demo.md). Show the queue before and at its deadline using the clock-controlled test below. | A promise is not a credit. When it lapses, the row can reappear with a reason, subject to other holds and calling hours. |
| 1:15–1:45 | Pay a correctly linked installment at **sandbox** checkout. Re-read `GET /queue` after the signed notification; if delivery isn't wired, call `POST /queue/{iid}/refresh` and label it manual. | A ₹500 payment on ₹1,200 leaves ₹700 even on repeat refresh. Full verified payment moves the row to `other` with status `paid`. An HTTP 200 alone is not proof of payment or call pickup. [Receiver contract](webhook-contract.md#confirm-checkout) |
| 1:45–2:00 | Show the held-out evaluation at K=3. | Preview found two payers vs one for ID order, but ₹1,000 vs ₹1,200 in this seven-day synthetic book. No name/language swap changed the order. This is not a causal uplift or real-world fairness claim. |

From the repository root, using Python 3.13 and `calltrigger-api/requirements.txt`:

```sh
python -m evaluation.scorecard --k 3
python -m pytest -q calltrigger-api/test_promise_reminders.py calltrigger-api/test_cashfree_webhook.py calltrigger-api/test_dispatch_ledger.py
```

**What the team has actually observed:** The repository records an accepted Relay sandbox webhook and an Indus attempt ID, separate sandbox link creation, checkout, and a confirmed ₹1,200 lookup. The new receiver, queue transitions, missed promises, and restart/race behavior have automated fixture evidence. A single live run connecting **call pickup → in-call link request → checkout → signed delivery to this deployed app** still needs to be demonstrated. When showing fixtures, say so. [Relay setup](relay-setup.md) · [Notes with source quotes](review-call-notes.md) · [Ranking scorecard](../evaluation/README.md).
