"""Borrower agreements pause outreach; only verified payments change the balance."""
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field, StrictFloat, StrictInt, StrictStr, field_validator

import payment_store as store
from queue_balance import IST, to_paise


class PromiseRequest(BaseModel, extra="forbid"):
    amount: StrictInt | StrictFloat | StrictStr = Field(
        description="INR rupees, at most two decimal places.", examples=["250.25"])
    promise_at: AwareDatetime = Field(description="Future payment deadline with a UTC offset; displayed in IST.")

    @field_validator("promise_at", mode="before")
    @classmethod
    def dated_timestamp(cls, value):
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("Use a dated timestamp, e.g. 2026-11-24T14:00:00+05:30")
        return value


class ActivePromiseError(Exception):
    pass


def _state(promise, paid, now):
    if paid - promise["baseline_paid_paise"] >= promise["promised_paise"]:
        return "kept"
    return "active" if now < datetime.fromisoformat(promise["promise_at"]) else "lapsed"


def record_promise(iid, request, now):
    with store._existing_for_update(iid) as (db, record):
        paise = to_paise(request.amount)
        if request.promise_at <= now:
            raise ValueError("Choose a future payment deadline with a time zone.")
        try:
            at = request.promise_at.astimezone(IST).isoformat()
        except OverflowError:
            raise ValueError("Payment deadline is outside the supported date range in IST.") from None
        previous = record.get("promise")
        if previous and (previous["promised_paise"], previous["promise_at"]) == (paise, at):
            return record  # A retry must not reset the amount paid at signing.
        paid = record["paid_paise"]
        if not 0 < paise <= record["amount_paise"] - paid:
            raise ValueError("Promised INR amount must be positive and no greater than the remaining balance.")
        if previous and _state(previous, paid, now) == "active":
            raise ActivePromiseError("This installment already has an active promise.")
        db.execute("""INSERT INTO payment_promises (installment_id, promise_at, promised_paise, baseline_paid_paise)
                      VALUES (?, ?, ?, ?) ON CONFLICT(installment_id) DO UPDATE SET
                      promise_at=excluded.promise_at, promised_paise=excluded.promised_paise,
                      baseline_paid_paise=excluded.baseline_paid_paise""", (iid, at, paise, paid))
        return {**record, "promise": {"promise_at": at, "promised_paise": paise, "baseline_paid_paise": paid}}


def _inr(paise):
    return f"₹{paise // 100}.{paise % 100:02d}"


def apply_to_queue(record, now, status, reason):
    promise = record.get("promise")
    if not promise:
        return status, reason
    paid = record["paid_paise"]
    state = _state(promise, paid, now)
    amount = _inr(promise["promised_paise"])
    since = _inr(paid - promise["baseline_paid_paise"])
    at = datetime.fromisoformat(promise["promise_at"])
    precision = "microseconds" if at.microsecond else "seconds" if at.second else "minutes"
    deadline = at.replace(tzinfo=None).isoformat(sep=" ", timespec=precision) + " IST"
    if state == "active":
        note = f"Promise to pay {amount} by {deadline}; collection contact is paused."
        if status == "would_call":
            return "promise_wait", note
    elif state == "kept":
        note = f"Promise kept: {since} verified since the {amount} promise."
    else:
        note = f"Lapsed promise: {amount} was due by {deadline}; {since} verified since the promise."
    return status, f"{reason.rstrip('.')}. {note}"
