"""Borrower contact stops for one lender, keyed by the installment's registered phone."""
import sqlite3
from contextlib import closing, contextmanager
from typing import Literal

from pydantic import BaseModel

from payment_store import database_path


class Request(BaseModel, extra="forbid"):
    reason: Literal["no_contact", "hardship"]


_REASONS = {
    "no_contact": "Borrower requested no contact. Do not call or message. Human support is available if they reach out.",
    "hardship": "Borrower reported hardship. Automated outreach stopped. Offer human support only if they ask.",
}
_SUPPORT_KN = "ಸ್ವಯಂಚಾಲಿತ ಕರೆಗಳು ಮತ್ತು ಸಂದೇಶಗಳನ್ನು ನಿಲ್ಲಿಸಲಾಗಿದೆ. ಸಹಾಯ ಬೇಕಿದ್ದರೆ ನಮ್ಮ ತಂಡವನ್ನು ಸಂಪರ್ಕಿಸಬಹುದು."


@contextmanager
def _table():
    with closing(sqlite3.connect(database_path())) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS borrower_contact_preferences (
            phone_number TEXT PRIMARY KEY NOT NULL,
            reason TEXT NOT NULL CHECK (reason IN ('no_contact', 'hardship'))
        )""")
        yield db


def record(phone, reason):
    with _table() as db:
        # A later hardship report must never weaken an explicit no-contact request.
        db.execute("""INSERT INTO borrower_contact_preferences (phone_number, reason) VALUES (?, ?)
                      ON CONFLICT(phone_number) DO UPDATE SET reason = excluded.reason
                      WHERE borrower_contact_preferences.reason != 'no_contact'""", (phone, reason))


def for_phone(phone, *, db=None):
    if db is not None:
        row = db.execute("SELECT reason FROM borrower_contact_preferences WHERE phone_number = ?", (phone,)).fetchone()
        return row[0] if row else None
    with _table() as db:
        return for_phone(phone, db=db)


def all_by_phone():
    with _table() as db:
        return dict(db.execute("SELECT phone_number, reason FROM borrower_contact_preferences"))


def decision(preference, status, reason):
    if preference is None:
        return status, reason
    notice = f"{_REASONS[preference]} {_SUPPORT_KN}"
    if status in ("paid", "payment_hold"):
        return status, f"{reason} {notice}"
    return preference, notice
