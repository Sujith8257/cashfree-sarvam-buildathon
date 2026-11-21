"""Trigger API: photo of the lender's notebook -> Sarvam Document AI -> borrowers due -> call API."""
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from dotenv import load_dotenv, set_key
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Security, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import cashfree_status
import payment_store as store
from review_notes import router as notes_router
from queue_balance import installment_id, outreach_state, to_paise

ENV_FILE = Path(__file__).with_name(".env")
load_dotenv(ENV_FILE)
if not os.getenv("TRIGGER_API_KEY"):  # first start: create the key callers must send, saved in .env
    os.environ["TRIGGER_API_KEY"] = secrets.token_urlsafe(32)
    set_key(ENV_FILE, "TRIGGER_API_KEY", os.environ["TRIGGER_API_KEY"])
SARVAM_KEY = os.getenv("SARVAM_API_KEY")
TRIGGER_KEY = os.environ["TRIGGER_API_KEY"]   # callers send this in the X-API-Key header
CALL_API_URL = os.getenv("CALL_API_URL")      # your friend's "start a call" endpoint
CALL_API_TOKEN = os.getenv("CALL_API_TOKEN")  # optional, sent as a Bearer token

SARVAM_JOB = "https://api.sarvam.ai/doc-ai/v1/job"
IST = timezone(timedelta(hours=5, minutes=30))
CALL_START, CALL_END = 8, 19                  # RBI: contact borrowers only 8 AM-7 PM
REMIND_DAYS_BEFORE = 1                        # call if due tomorrow, today or overdue
LANGS = {"hindi": "hi-IN", "english": "en-IN", "kannada": "kn-IN", "tamil": "ta-IN",
         "telugu": "te-IN", "marathi": "mr-IN", "bengali": "bn-IN", "gujarati": "gu-IN",
         "malayalam": "ml-IN", "punjabi": "pa-IN", "odia": "od-IN", "assamese": "as-IN",
         "sanskrit": "sa-IN"}
RELAY_LANGUAGES = {code: name.title() for name, code in LANGS.items()}

SCHEMA = {
    "type": "object",
    "properties": {
        "borrowers": {
            "type": "array",
            "description": "One entry per borrower row in the lender's loan notebook",
            "items": {
                "type": "object",
                "description": "One borrower row",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer ID written for the borrower, e.g. C001"},
                    "name": {"type": "string", "description": "Borrower's full name exactly as written"},
                    "phone_number": {"type": "string", "description": "Borrower's 10-digit mobile number, digits only"},
                    "email": {"type": "string", "description": "Borrower's email address, if written"},
                    "language": {"type": "string", "description": "Language the borrower speaks, as an English name such as Hindi, Kannada or Tamil"},
                    "lending_date": {"type": "string", "description": "Date the loan was given, as YYYY-MM-DD"},
                    "due_date": {"type": "string", "description": "Date the repayment is due, as YYYY-MM-DD"},
                    "outstanding_amount": {"type": "number", "description": "Amount still to be repaid, in INR, digits only"},
                    "principal_amount": {"type": "number", "description": "Original loan amount given, in INR, digits only"},
                    "interest_rate": {"type": "number", "description": "Interest rate in percent, number only, e.g. 2 for 2%"},
                },
            },
        }
    },
}

app = FastAPI(title="Loan call trigger")
triggered = set()  # shortcut: in-memory, forgets on restart; use a DB table before real use


def require_key(key: str = Security(APIKeyHeader(name="X-API-Key"))):
    if not secrets.compare_digest(key.encode(), TRIGGER_KEY.encode()):
        raise HTTPException(401, "Invalid API key")


def read_notebook(data, filename, content_type, language):
    """Send the notebook page to Sarvam Document AI (Extract) and wait for the borrower rows."""
    if not SARVAM_KEY:
        raise HTTPException(503, "Notebook OCR requires SARVAM_API_KEY")
    headers = {"api-subscription-key": SARVAM_KEY}
    form = {"schema": json.dumps(SCHEMA), "output_format": "json"}
    if language:
        form["language"] = language
    r = requests.post(f"{SARVAM_JOB}/extract", headers=headers, data=form,
                      files={"file": (filename, data, content_type)}, timeout=60)
    if not r.ok:
        raise HTTPException(502, f"Sarvam rejected the upload: {r.status_code} {r.text[:300]}")
    job_id = r.json()["job_id"]
    for _ in range(90):  # up to ~3 minutes
        status = requests.get(f"{SARVAM_JOB}/{job_id}/status", headers=headers, timeout=30).json()["status"].lower()
        if status in ("completed", "partially_completed"):
            result = requests.get(f"{SARVAM_JOB}/{job_id}/results", headers=headers, timeout=30).json()["result"]
            return result.get("borrowers") or []
        if status in ("failed", "rejected"):
            raise HTTPException(502, f"Sarvam job {job_id} {status}")
        time.sleep(2)
    raise HTTPException(504, f"Sarvam job {job_id} is still running, try again")


def ascii_digits(text):
    """Turn Devanagari/Kannada/Tamil digits into 0-9, keep everything else."""
    return "".join(str(int(c)) if c.isdecimal() else c for c in ("" if text is None else str(text)))


def parse_phone(text):
    digits = re.sub(r"[\s()-]", "", ascii_digits(text))
    match = re.fullmatch(r"(?:\+?91|0)?([6-9][0-9]{9})", digits)
    return match[1] if match else None


def parse_date(text):
    text = ascii_digits(text).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_number(value):
    m = re.search(r"\d[\d,]*(?:\.\d+)?", ascii_digits(value))
    return float(m.group().replace(",", "")) if m else None


def relay_call_payload(customer):
    """Translate the notebook API's customer record to the Relay call trigger contract."""
    iid = customer["installment_id"]
    return {
        **customer,
        "event": "start_collection_call",
        "request_id": customer["trigger_id"],
        "borrower_id": customer["customer_id"],
        "borrower_name": customer["name"],
        "phone": f"+91{customer['phone_number']}",
        "preferred_language": RELAY_LANGUAGES.get(customer["language"], "Hindi"),
        "amount_due": customer["outstanding_amount"],
        "currency": "INR",
        "days_past_due": customer["days_overdue"],
        "link_id": f"emi-{iid}",
    }


def now_ist():
    return datetime.now(IST)


def daily_trigger_id(record, today):
    return f"{record['customer_id'] or record['phone_number']}-{record['due_date']}-{today}"


def queue_entry(record, now):
    """Use the same current balance, holds and contact rules for display and dispatch."""
    today = now.date()
    days = (today - datetime.fromisoformat(record["due_date"]).date()).days
    status, reason = outreach_state(record, now)
    if status is None:
        if days < -REMIND_DAYS_BEFORE:
            status, reason = "not_due", f"due on {record['due_date']}, too early to call"
        elif not CALL_START <= now.hour < CALL_END:
            status, reason = "blocked", "outside 8 AM-7 PM calling hours"
        elif daily_trigger_id(record, today) in triggered:
            status, reason = "skipped", "already called today for this due date"
        else:
            due_reason = (f"{days} day(s) overdue" if days > 0 else
                          "due today" if days == 0 else f"due in {-days} day(s), reminder")
            status, reason = "would_call", f"{reason}; {due_reason}" if reason else due_reason
    return {"installment_id": record["installment_id"], "customer_id": record["customer_id"],
            "name": record["name"], "due_date": record["due_date"], "days_overdue": max(0, days),
            "outstanding_amount": (record["amount_paise"] - record["paid_paise"]) / 100,
            "paid_amount": record["paid_paise"] / 100, "callback_at": record["callback_at"],
            "status": status, "reason": reason}


def check_and_call(row, dry_run, now=None):
    """Register valid notebook rows even when outreach is deferred. Only dispatch eligible rows."""
    now = now or now_ist()
    customer_id = str(row.get("customer_id") or "").strip()
    name = str(row.get("name") or "").strip() or "Unknown"
    phone = parse_phone(row.get("phone_number"))
    due = parse_date(row.get("due_date"))

    def skip(status, reason):
        return {"customer_id": customer_id, "name": name, "status": status, "reason": reason}

    if not phone:
        return skip("needs_check", f"phone number unreadable: {row.get('phone_number')!r}")
    if not due:
        return skip("needs_check", f"due date unreadable: {row.get('due_date')!r}")
    try:
        outstanding = to_paise(row.get("outstanding_amount"))
    except ValueError:
        return skip("needs_check", "outstanding amount unreadable")
    profile = {"customer_id": customer_id, "name": name, "phone_number": phone, "due_date": due.isoformat()}
    iid = installment_id(customer_id, phone, profile["due_date"])
    if outstanding <= 0:
        previous = store.get(iid)
        if previous is None:
            return skip("skipped", "nothing outstanding")
        if previous["phone_number"] != phone:
            return skip("needs_check", "notebook phone conflicts with the registered installment")
        # A zero on paper pauses reminders; only Cashfree can confirm payment.
        return queue_entry(store.mark_claim(iid), now)
    try:
        record = store.register(iid, profile, outstanding)
    except ValueError:
        return skip("needs_check", "notebook details conflict with the registered installment")
    entry = queue_entry(record, now)
    if entry["status"] != "would_call":
        return entry

    trigger_id = daily_trigger_id(record, now.date())
    lang = str(row.get("language") or "").strip()
    lending = parse_date(row.get("lending_date"))
    payload = {
        "trigger_id": trigger_id,  # same borrower + due date + day = same id, so a retry can be ignored
        "installment_id": iid,
        "customer_id": customer_id,
        "name": name,
        "phone_number": phone,
        "email": str(row.get("email") or "").strip(),
        "language": lang if re.fullmatch(r"[a-z]{2,3}-IN", lang) else LANGS.get(lang.lower(), "hi-IN"),
        "lending_date": lending.isoformat() if lending else None,
        "due_date": due.isoformat(),
        "outstanding_amount": entry["outstanding_amount"],
        "principal_amount": parse_number(row.get("principal_amount")),
        "interest_rate": parse_number(row.get("interest_rate")),
        "days_overdue": entry["days_overdue"],
        "reason": entry["reason"],
    }
    if dry_run:
        return {**payload, "status": "would_call"}
    if not CALL_API_URL:
        return {**payload, "status": "call_api_not_set", "reason": "set CALL_API_URL in .env"}
    headers = {"Authorization": f"Bearer {CALL_API_TOKEN}"} if CALL_API_TOKEN else {}
    endpoint = urlsplit(CALL_API_URL)
    is_relay = (endpoint.scheme == "https" and endpoint.hostname == "sandbox.cashfree.com"
                and endpoint.path.startswith("/relay/inbound/webhook/"))
    outbound = {"data": relay_call_payload(payload)} if is_relay else payload
    try:
        r = requests.post(CALL_API_URL, json=outbound, headers=headers, timeout=15)
    except requests.RequestException as e:
        return {**payload, "status": "call_api_error", "reason": str(e)}
    if not r.ok:
        return {**payload, "status": "call_api_error", "reason": f"{r.status_code} {r.text[:200]}"}
    triggered.add(trigger_id)
    return {**payload, "status": "call_triggered"}


def ranked_queue(results):
    eligible = (r for r in results if r["status"] == "would_call")
    return [{**r, "rank": rank} for rank, r in
            enumerate(sorted(eligible, key=lambda r: r["due_date"]), start=1)]


@app.post("/trigger/notebook", dependencies=[Depends(require_key)])
def trigger_from_notebook(file: UploadFile = File(...), language: str = Form(""), dry_run: bool = Form(False)):
    """Upload a notebook page. With dry_run=true, preview whom to call first by earliest due date."""
    rows = read_notebook(file.file.read(), file.filename, file.content_type, language)
    results = [check_and_call(row, dry_run) for row in rows]
    response = {"rows_read": len(rows),
                "calls": sum(r["status"] in ("call_triggered", "would_call") for r in results),
                "results": results,
                "extracted": rows}
    if dry_run:
        fields = ("rank", "installment_id", "customer_id", "name", "due_date", "outstanding_amount", "reason")
        response["call_queue"] = [{key: r[key] for key in fields} for r in ranked_queue(results)]
    return response


class Borrower(BaseModel):
    customer_id: str = ""
    name: str
    phone_number: str
    email: str = ""
    language: str = "Hindi"
    lending_date: str = ""
    due_date: str  # YYYY-MM-DD or DD/MM/YYYY
    outstanding_amount: float
    principal_amount: float = 0
    interest_rate: float = 0


@app.post("/trigger/call", dependencies=[Depends(require_key)])
def trigger_one(borrower: Borrower, dry_run: bool = False):
    """Trigger one call from typed-in details (no photo). Handy for testing the call API."""
    return check_and_call(dict(borrower), dry_run)


queue_api = APIRouter(prefix="/queue", dependencies=[Depends(require_key)])


def get_installment(iid):
    record = store.get(iid)
    if record is None:
        raise HTTPException(404, "Installment not found")
    return record


@queue_api.get("")
def lender_queue():
    """Evaluate the stored installments at read time, including callbacks that just became due."""
    now = now_ist()
    rows = [queue_entry(record, now) for record in store.all_installments()]
    return {"as_of": now.isoformat(), "call_queue": ranked_queue(rows),
            "other": [r for r in rows if r["status"] != "would_call"]}


@queue_api.post("/{iid}/refresh")
def refresh_payment(iid: str):
    record = get_installment(iid)
    try:
        paid = cashfree_status.fetch_paid_paise(record["link_id"], record["amount_paise"], record["phone_number"])
    except cashfree_status.PaymentLookupError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    return queue_entry(store.record_payment(iid, paid), now_ist())


@queue_api.post("/{iid}/already-paid")
def report_paid(iid: str):
    get_installment(iid)
    return queue_entry(store.mark_claim(iid), now_ist())


class CallbackRequest(BaseModel):
    callback_at: datetime


@queue_api.post("/{iid}/callback")
def schedule_callback(iid: str, request: CallbackRequest):
    get_installment(iid)
    now = now_ist()
    at = request.callback_at
    if at.utcoffset() is None:
        raise HTTPException(422, "Include the time zone, e.g. +05:30 for India")
    at = at.astimezone(IST)
    if at <= now or not CALL_START <= at.hour < CALL_END:
        raise HTTPException(422, "Choose a future callback between 08:00 and 19:00 IST (before 19:00)")
    return queue_entry(store.set_callback(iid, at.isoformat()), now)


queue_api.include_router(notes_router)
app.include_router(queue_api)
LENDER_DIR = Path(__file__).with_name("lender")
app.mount("/lender/assets", StaticFiles(directory=LENDER_DIR), name="lender-assets")


@app.get("/lender", include_in_schema=False)
def lender_screen():
    return FileResponse(LENDER_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
