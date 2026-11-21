"""SQLite-backed installment balances and outreach holds."""
import os
import re
import sqlite3
from contextlib import closing, contextmanager
from datetime import date, datetime
from pathlib import Path


_INSTALLMENTS = """SELECT i.*, p.promise_at, p.promised_paise, p.baseline_paid_paise
                   FROM installments i LEFT JOIN payment_promises p USING (installment_id)"""


@contextmanager
def _connection(*, write=False):
    path = os.getenv("COLLECTIONS_DB") or Path(__file__).with_name("collections.sqlite3")
    with closing(sqlite3.connect(path)) as db, db:
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS installments (
            installment_id TEXT PRIMARY KEY NOT NULL,
            customer_id TEXT NOT NULL,
            name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            due_date TEXT NOT NULL,
            amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
            paid_paise INTEGER NOT NULL DEFAULT 0 CHECK (paid_paise BETWEEN 0 AND amount_paise),
            claimed_paid INTEGER NOT NULL DEFAULT 0 CHECK (claimed_paid IN (0, 1)),
            callback_at TEXT
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS payment_promises (
            installment_id TEXT PRIMARY KEY NOT NULL REFERENCES installments(installment_id),
            promise_at TEXT NOT NULL,
            promised_paise INTEGER NOT NULL CHECK (promised_paise > 0),
            baseline_paid_paise INTEGER NOT NULL CHECK (baseline_paid_paise >= 0)
        )""")
        if write:
            # Keep a decision based on stored state and its write in one transaction.
            db.execute("BEGIN IMMEDIATE")
        yield db


def _record(row):
    record = dict(row)
    promise = {key: record.pop(key) for key in ("promise_at", "promised_paise", "baseline_paid_paise")}
    if promise["promise_at"] is not None:
        record["promise"] = promise
    return {**record, "link_id": f"emi-{row['installment_id']}", "claimed_paid": bool(row["claimed_paid"])}


def _get(db, installment_id):
    row = db.execute(_INSTALLMENTS + " WHERE i.installment_id = ?", (installment_id,)).fetchone()
    return _record(row) if row is not None else None


def get(installment_id: str) -> dict | None:
    with _connection() as db:
        return _get(db, installment_id)


def all_installments() -> list[dict]:
    with _connection() as db:
        return [_record(row) for row in db.execute(_INSTALLMENTS + " ORDER BY i.rowid")]


def _validate_paise(value):
    if type(value) is not int or not 0 <= value < 2**63:
        raise ValueError("paise must be a nonnegative signed 64-bit integer")


def register(installment_id: str, profile: dict, amount_paise: int) -> dict:
    _validate_paise(amount_paise)
    if not isinstance(installment_id, str) or not installment_id.strip():
        raise ValueError("installment_id must be nonempty text")
    fields = ("customer_id", "name", "phone_number", "due_date")
    if not isinstance(profile, dict) or not all(isinstance(profile.get(key), str) for key in fields):
        raise ValueError("customer_id, name, phone_number and due_date must be strings")
    if not re.fullmatch(r"[6-9][0-9]{9}", profile["phone_number"]):
        raise ValueError("phone_number must be a canonical 10-digit Indian mobile number")
    if date.fromisoformat(profile["due_date"]).isoformat() != profile["due_date"]:
        raise ValueError("due_date must be YYYY-MM-DD")
    with _connection(write=True) as db:
        existing = _get(db, installment_id)
        if existing is not None:
            if existing["phone_number"] != profile["phone_number"]:
                raise ValueError("installment phone_number conflicts with the original registration")
            original = existing["amount_paise"]
            if amount_paise not in (original, original - existing["paid_paise"]):
                raise ValueError("amount_paise must match the original amount or verified remaining balance")
            return existing
        if amount_paise == 0:
            raise ValueError("a new installment must have a positive amount_paise")
        db.execute("""INSERT INTO installments (installment_id, customer_id, name, phone_number, due_date, amount_paise)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (installment_id, profile["customer_id"], profile["name"], profile["phone_number"],
                    profile["due_date"], amount_paise))
        return _get(db, installment_id)


@contextmanager
def _existing_for_update(installment_id):
    with _connection(write=True) as db:
        record = _get(db, installment_id)
        if record is None:
            raise KeyError(installment_id)
        yield db, record


def record_payment(installment_id: str, paid_paise: int) -> dict:
    """Apply a cumulative verified total. Repeated or older totals have no effect."""
    with _existing_for_update(installment_id) as (db, record):
        _validate_paise(paid_paise)
        if paid_paise > record["amount_paise"]:
            raise ValueError("paid_paise exceeds the original installment amount")
        if paid_paise <= record["paid_paise"]:
            return record
        db.execute("UPDATE installments SET paid_paise = ? WHERE installment_id = ?", (paid_paise, installment_id))
        return {**record, "paid_paise": paid_paise}


def mark_claim(installment_id: str) -> dict:
    with _existing_for_update(installment_id) as (db, record):
        db.execute("UPDATE installments SET claimed_paid = 1 WHERE installment_id = ?", (installment_id,))
        return {**record, "claimed_paid": True}


def set_callback(installment_id: str, callback_at: str) -> dict:
    with _existing_for_update(installment_id) as (db, record):
        if not isinstance(callback_at, str) or datetime.fromisoformat(callback_at).utcoffset() is None:
            raise ValueError("callback_at must be a timezone-aware ISO timestamp")
        db.execute("UPDATE installments SET callback_at = ? WHERE installment_id = ?", (callback_at, installment_id))
        return {**record, "callback_at": callback_at}
