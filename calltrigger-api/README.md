# Loan call trigger API

The lender photographs the loan notebook. Sarvam Document AI reads every row, and every borrower who is due gets a call triggered on the call API.

## Run

1. `pip install -r requirements.txt`
2. In `.env`, set `CALL_API_URL` to the call API. Leave it empty to test with dry runs.
3. `python trigger_api.py`, then open http://localhost:8000/docs
4. The trigger key (`TRIGGER_API_KEY`) is created in `.env` on first start. Send it as the `X-API-Key` header (in `/docs`: **Authorize**).

```powershell
curl.exe -X POST http://localhost:8000/trigger/notebook -H "X-API-Key: <TRIGGER_API_KEY>" -F "file=@sample_notebook.png" -F "dry_run=true"
```

### Who should I call first?

The notebook dry run above returns `call_queue`. Read it from rank 1: only `would_call` rows appear, earliest due date first. Ties keep their notebook order. Each entry includes the borrower, outstanding amount in INR, and the reason from the eligibility check:

```json
{"rank": 1, "customer_id": "C001", "name": "Meera", "due_date": "2026-11-16", "outstanding_amount": 800, "reason": "5 day(s) overdue"}
```

If no one can be called (including outside calling hours), `call_queue` is `[]`. Check `results` for every row in its original order and the reason it was included or skipped. A dry run does not place calls.

## Endpoints

| Method | Path | Input | What it does |
|---|---|---|---|
| POST | `/trigger/notebook` | form-data: `file` (JPG/PNG/PDF), optional `language` (e.g. `hi-IN`), `dry_run` | Reads the page and triggers a call for every borrower who is due |
| POST | `/trigger/call` | JSON with the notebook fields, `?dry_run=true` optional | Triggers one call without a photo |

Notebook fields read: `customer_id, name, phone_number, email, language, lending_date, due_date, outstanding_amount, principal_amount, interest_rate`

## Rules

- Calls only borrowers due tomorrow, today or overdue
- Only between 8 AM and 7 PM IST (RBI); otherwise `blocked`
- Unreadable phone, due date or amount: `needs_check`, no call
- One call per borrower per due date per day
- `dry_run=true` shows who would be called, without calling

## What the call API receives

`POST CALL_API_URL` with this JSON (`Authorization: Bearer CALL_API_TOKEN` if set). Any 2xx means the call started. Ignore a `trigger_id` you have already seen: it's a retry, not a new call.

```json
{
  "trigger_id": "C001-2026-11-20-2026-11-21",
  "customer_id": "C001",
  "name": "Ramesh Kumar",
  "phone_number": "9876543210",
  "email": "ramesh.k@gmail.com",
  "language": "hi-IN",
  "lending_date": "2026-08-21",
  "due_date": "2026-11-20",
  "outstanding_amount": 4500.0,
  "principal_amount": 15000.0,
  "interest_rate": 2.0,
  "days_overdue": 1,
  "reason": "1 day(s) overdue"
}
```

## Tests

`python -m pytest -q`
