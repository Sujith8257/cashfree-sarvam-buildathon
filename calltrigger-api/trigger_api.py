"""Trigger API: photo of the lender's notebook -> Sarvam Document AI -> borrowers due -> call API."""
import hashlib
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
from fastapi import Depends, FastAPI, File, Form, HTTPException, Security, UploadFile
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

ENV_FILE = Path(__file__).with_name(".env")
load_dotenv(ENV_FILE)
if not os.getenv("TRIGGER_API_KEY"):  # first start: create the key callers must send, saved in .env
    os.environ["TRIGGER_API_KEY"] = secrets.token_urlsafe(32)
    set_key(ENV_FILE, "TRIGGER_API_KEY", os.environ["TRIGGER_API_KEY"])
SARVAM_KEY = os.environ["SARVAM_API_KEY"]
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
    digits = re.sub(r"\D", "", ascii_digits(text))[-10:]
    return digits if re.fullmatch(r"[6-9]\d{9}", digits) else None


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
    installment_ref = f"{customer['customer_id'] or customer['phone_number']}:{customer['due_date']}"
    installment_id = hashlib.sha256(installment_ref.encode()).hexdigest()[:24]
    return {
        **customer,
        "event": "start_collection_call",
        "request_id": customer["trigger_id"],
        "borrower_id": customer["customer_id"],
        "installment_id": installment_id,
        "borrower_name": customer["name"],
        "phone": f"+91{customer['phone_number']}",
        "preferred_language": RELAY_LANGUAGES.get(customer["language"], "Hindi"),
        "amount_due": customer["outstanding_amount"],
        "currency": "INR",
        "days_past_due": customer["days_overdue"],
        "link_id": f"emi-{installment_id}",
    }


def check_and_call(row, dry_run, now=None):
    """Apply the rules to one notebook row; trigger the call only if every rule passes."""
    now = now or datetime.now(IST)
    today = now.date()
    customer_id = str(row.get("customer_id") or "").strip()
    name = str(row.get("name") or "").strip() or "Unknown"
    phone = parse_phone(row.get("phone_number"))
    due = parse_date(row.get("due_date"))
    outstanding = parse_number(row.get("outstanding_amount"))

    def skip(status, reason):
        return {"customer_id": customer_id, "name": name, "status": status, "reason": reason}

    if not phone:
        return skip("needs_check", f"phone number unreadable: {row.get('phone_number')!r}")
    if not due:
        return skip("needs_check", f"due date unreadable: {row.get('due_date')!r}")
    if outstanding is None:
        return skip("needs_check", f"outstanding amount unreadable: {row.get('outstanding_amount')!r}")
    if outstanding <= 0:
        return skip("skipped", "nothing outstanding")
    if due > today + timedelta(days=REMIND_DAYS_BEFORE):
        return skip("not_due", f"due on {due}, too early to call")
    if not CALL_START <= now.hour < CALL_END:
        return skip("blocked", "outside 8 AM-7 PM calling hours")
    trigger_id = f"{customer_id or phone}-{due}-{today}"
    if trigger_id in triggered:
        return skip("skipped", "already called today for this due date")

    overdue = (today - due).days
    lang = str(row.get("language") or "").strip()
    lending = parse_date(row.get("lending_date"))
    payload = {
        "trigger_id": trigger_id,  # same borrower + due date + day = same id, so a retry can be ignored
        "customer_id": customer_id,
        "name": name,
        "phone_number": phone,
        "email": str(row.get("email") or "").strip(),
        "language": lang if re.fullmatch(r"[a-z]{2,3}-IN", lang) else LANGS.get(lang.lower(), "hi-IN"),
        "lending_date": lending.isoformat() if lending else None,
        "due_date": due.isoformat(),
        "outstanding_amount": outstanding,
        "principal_amount": parse_number(row.get("principal_amount")),
        "interest_rate": parse_number(row.get("interest_rate")),
        "days_overdue": max(overdue, 0),
        "reason": f"{overdue} day(s) overdue" if overdue > 0
                  else "due today" if overdue == 0 else f"due in {-overdue} day(s), reminder",
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
        eligible = (r for r in results if r["status"] == "would_call")
        fields = ("customer_id", "name", "due_date", "outstanding_amount", "reason")
        response["call_queue"] = [
            {"rank": rank, **{key: r[key] for key in fields}}
            for rank, r in enumerate(sorted(eligible, key=lambda r: r["due_date"]), start=1)
        ]
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
