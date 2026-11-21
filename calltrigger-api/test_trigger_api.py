import os
from datetime import date, datetime

os.environ.setdefault("SARVAM_API_KEY", "test-sarvam-key")
os.environ["TRIGGER_API_KEY"] = "test-trigger-key"
os.environ["CALL_API_URL"] = "http://call-api.test/call"

import pytest
from fastapi.testclient import TestClient

import trigger_api as t

NOON = datetime(2026, 11, 21, 12, 0, tzinfo=t.IST)


def row(**overrides):
    base = {
        "customer_id": "C001", "name": "Ramesh Kumar", "phone_number": "9876543210",
        "email": "ramesh@example.com", "language": "Kannada", "lending_date": "2026-08-21",
        "due_date": "2026-11-20", "outstanding_amount": 4500, "principal_amount": 15000,
        "interest_rate": "2%",
    }
    return {**base, **overrides}


@pytest.fixture(autouse=True)
def fresh_state():
    t.triggered.clear()


def test_phone_with_country_code_and_hindi_digits_is_read():
    assert t.parse_phone("+91 ९८७६५४३२१०") == "9876543210"
    assert t.parse_phone("98765") is None


def test_indian_date_formats_are_read():
    assert t.parse_date("20/11/2026") == date(2026, 11, 20)
    assert t.parse_date("२०-११-२०२६") == date(2026, 11, 20)
    assert t.parse_date("next friday") is None


def test_overdue_borrower_would_be_called_with_all_notebook_fields():
    result = t.check_and_call(row(), dry_run=True, now=NOON)
    assert result["status"] == "would_call"
    assert result["language"] == "kn-IN"
    assert result["days_overdue"] == 1
    assert result["customer_id"] == "C001"
    assert result["email"] == "ramesh@example.com"
    assert result["lending_date"] == "2026-08-21"
    assert result["principal_amount"] == 15000
    assert result["interest_rate"] == 2.0


def test_borrower_due_next_week_is_not_called():
    assert t.check_and_call(row(due_date="2026-11-28"), dry_run=True, now=NOON)["status"] == "not_due"


def test_no_calls_after_7pm():
    late = NOON.replace(hour=19, minute=5)
    assert t.check_and_call(row(), dry_run=True, now=late)["status"] == "blocked"


def test_unreadable_phone_is_not_called():
    assert t.check_and_call(row(phone_number="98x76"), dry_run=True, now=NOON)["status"] == "needs_check"


def test_nothing_outstanding_is_not_called():
    assert t.check_and_call(row(outstanding_amount=0), dry_run=True, now=NOON)["status"] == "skipped"


def test_same_borrower_is_called_once_per_day(monkeypatch):
    sent = []

    class Ok:
        ok = True

    monkeypatch.setattr(t.requests, "post", lambda url, json, headers, timeout: sent.append(json) or Ok())
    assert t.check_and_call(row(), dry_run=False, now=NOON)["status"] == "call_triggered"
    assert t.check_and_call(row(), dry_run=False, now=NOON)["status"] == "skipped"
    assert len(sent) == 1
    assert sent[0]["phone_number"] == "9876543210"


def test_wrong_api_key_is_rejected():
    client = TestClient(t.app)
    body = {"name": "Ramesh Kumar", "phone_number": "9876543210",
            "due_date": "2026-11-20", "outstanding_amount": 4500}
    assert client.post("/trigger/call?dry_run=true", json=body,
                       headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/trigger/call?dry_run=true", json=body,
                       headers={"X-API-Key": "test-trigger-key"}).status_code == 200
