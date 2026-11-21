"""At most one potentially accepted POST per installment and IST day in COLLECTIONS_DB."""
import sqlite3
from contextlib import contextmanager

import requests

from payment_store import _connection


@contextmanager
def _ledger(*, write=False):
    with _connection(write=write) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS dispatch_ledger (
            installment_id TEXT NOT NULL, ist_day TEXT NOT NULL,
            state TEXT NOT NULL CHECK (state IN ('unknown', 'queued', 'accepted')),
            PRIMARY KEY (ist_day, installment_id)
        )""")
        yield db


def _state(db, key):
    row = db.execute("SELECT state FROM dispatch_ledger WHERE installment_id=? AND ist_day=?", key).fetchone()
    return row[0] if row else None


def state(key):
    with _ledger() as db:
        return _state(db, key)


def states_for_day(ist_day):
    with _ledger() as db:
        return dict(db.execute("SELECT installment_id, state FROM dispatch_ledger WHERE ist_day=?", (ist_day,)))


def _reserve(key, trigger_id, check_policy):
    """Commit unknown before sending: process death must never make this slot available."""
    with _ledger(write=True) as db:
        blocked = check_policy(db)
        if blocked:
            return blocked
        previous = _state(db, key)
        if previous is not None:
            return outcome(trigger_id, previous)
        db.execute("INSERT INTO dispatch_ledger (installment_id, ist_day, state) VALUES (?, ?, 'unknown')", key)
        return None


def outcome(trigger_id, state, status="skipped"):
    note = {"unknown": "Call acceptance is unknown.", "queued": "Reminder queued.",
            "accepted": "Call request accepted."}[state]
    action = f"Check provider or Relay logs for {trigger_id} to confirm the outcome."
    if state == "unknown":
        action += " Do not resend today."
    result = {"status": status, "dispatch_state": state, "trigger_id": trigger_id, "next_step": action}
    if status != "call_triggered":  # Keep the original eligibility reason on acknowledged calls.
        result["reason"] = f"{note} {action}"
    return result


def post_once(key, trigger_id, url, outbound, headers, *, relay, check_policy):
    blocked = _reserve(key, trigger_id, check_policy)
    if blocked is not None:
        return blocked
    try:
        # A 307/308 redirect would otherwise send a second POST on the same reservation.
        reply = requests.post(url, json=outbound, headers=headers, timeout=15, allow_redirects=False)
    except requests.ConnectTimeout:
        rejection = "Connection timed out before the request was sent"
    except requests.RequestException:
        return outcome(trigger_id, "unknown", "call_api_error")
    else:
        code = reply.status_code
        if 200 <= code < 300:
            delivery = "queued" if relay or code == 202 else "accepted"
            result = outcome(trigger_id, delivery, "call_triggered")
            try:
                with _ledger(write=True) as db:
                    db.execute("UPDATE dispatch_ledger SET state=? WHERE installment_id=? AND ist_day=?", (delivery, *key))
            except sqlite3.Error:  # The committed reservation still blocks a retry.
                result["next_step"] = f"Could not save the acknowledgment. {result['next_step']} Do not resend today."
            return result
        # A conflict can acknowledge a previous send; a gateway error can follow acceptance.
        if code not in (400, 401, 403, 404, 405, 410, 413, 415, 422):
            return outcome(trigger_id, "unknown", "call_api_error")
        rejection = f"Call API rejected the request (HTTP {code})"

    with _ledger(write=True) as db:
        db.execute("DELETE FROM dispatch_ledger WHERE installment_id=? AND ist_day=?", key)
    return {"status": "call_api_error", "dispatch_state": "rejected", "reason": f"{rejection}; correct the issue and retry."}
