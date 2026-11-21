# Demo: “I’ll pay ₹250.25 by 2 PM”

**Roughly two minutes, offline.** With the repository requirements installed, run this from the repository root:

```powershell
python -m pytest -q calltrigger-api/test_promise_reminders.py
```

The tests use a temporary SQLite file, a dummy API key, a fixed IST clock and simulated verified totals. No OCR, calls or payments take place. Two scenarios use a ₹1,200 installment:

| At the time of the promise | What happens next | What the lender sees |
| --- | --- | --- |
| ₹500 already verified; borrower promises another ₹250.25 | Verified total reaches ₹650 | No call: only ₹150 has been verified since the promise. ₹550 remains due. |
| Same agreement | Verified total reaches ₹750.25 | **Promise kept**. ₹449.75 remains due and normal queue rules apply. |
| Fresh installment, ₹0 verified; promise of ₹250.25 | Only ₹250.24 verified when 14:00 IST arrives | **Lapsed promise**. ₹949.76 remains due; if eligible, the installment returns to its usual due-date rank. |

## Try the action locally

1. Start the [local demo and register a synthetic installment](lender-queue-demo.md#2-register-meera-and-ravi-client-powershell) using `dry_run=true`. Open `http://127.0.0.1:8000/docs`, choose **Authorize**, and enter the local `X-API-Key`.
2. Open **POST `/queue/{iid}/promise`**. Paste the returned `installment_id`, choose a **future** date and time, and submit an amount no larger than the verified remaining balance. Example body (replace the date):

   ```json
   { "amount": "250.25", "promise_at": "2030-11-24T14:00:00+05:30" }
   ```

3. Open **GET `/queue`**. The row shows the deadline in IST. The `promise` object stores `promise_at`, `promised_paise` and `baseline_paid_paise` (100 paise = ₹1). `paid_amount` is unchanged and `callback_at` is independent. Restarting the API with the same `COLLECTIONS_DB` keeps the agreement.

Payment deadlines may be outside calling hours; an explicit UTC offset (or `Z`) is required. At the deadline, the queue compares the latest **verified cumulative total minus the stored baseline** to the promise. A pending payment claim, a future callback, full payment, the daily call limit and 08:00–19:00 IST calling hours keep their existing priority. A queue read never dials. No timer or additional payment lookup runs in the background.

Only the latest agreement is retained per installment. Retrying an identical future agreement preserves its baseline; a different agreement while one is active returns `409`. A kept or lapsed agreement can be replaced. An invalid amount, a past or timezone-free deadline, or unexpected fields returns `422`; an unknown installment returns `404`.
