import os
from datetime import date, datetime
from functools import partial

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
def fresh_state(tmp_path, monkeypatch):
    t.triggered.clear()
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "queue.sqlite3"))


def test_phone_with_country_code_and_hindi_digits_is_read():
    assert t.parse_phone("+91 ९८७६५४३२१०") == "9876543210"
    assert t.parse_phone("98765") is None
    assert t.parse_phone("wrong:0019876543210") is None


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


def test_overpayment_is_not_registered_as_positive_debt():
    assert t.check_and_call(row(outstanding_amount=-500), dry_run=True, now=NOON)["status"] == "skipped"


def test_zero_balance_rescan_holds_existing_installment_without_verifying_payment():
    t.check_and_call(row(), dry_run=True, now=NOON)
    hold = t.check_and_call(row(outstanding_amount=0), dry_run=True, now=NOON)
    assert hold["status"] == "payment_hold"
    assert hold["paid_amount"] == 0
    assert t.check_and_call(row(), dry_run=False, now=NOON)["status"] == "payment_hold"


def test_preview_registers_installment_for_queue_even_outside_calling_hours(monkeypatch):
    evening = NOON.replace(hour=20)
    monkeypatch.setattr(t, "now_ist", lambda: evening, raising=False)
    client = TestClient(t.app)
    response = client.post("/trigger/call?dry_run=true", json=row(interest_rate=2),
                           headers={"X-API-Key": "test-trigger-key"})
    assert response.status_code == 200
    installment = response.json()
    assert installment["status"] == "blocked"
    queue = client.get("/queue", headers={"X-API-Key": "test-trigger-key"})
    assert queue.status_code == 200
    assert queue.json()["call_queue"] == []
    assert [r["installment_id"] for r in queue.json()["other"]] == [installment["installment_id"]]


def test_notebook_preview_ranks_only_eligible_borrowers_by_due_date(monkeypatch):
    rows = [
        row(customer_id="tomorrow", due_date="2026-11-22"),
        row(customer_id="today", due_date="2026-11-21"),
        row(customer_id="paid", due_date="2026-11-01", outstanding_amount=0),
        row(customer_id="late", name="Meera", due_date="16/11/2026", outstanding_amount=800),
        row(customer_id="also-late", due_date="2026-11-16"),
    ]
    monkeypatch.setattr(t, "read_notebook", lambda *args: rows)
    monkeypatch.setattr(t, "check_and_call", partial(t.check_and_call, now=NOON))
    monkeypatch.setattr(t.requests, "post", lambda *a, **kw: pytest.fail("Preview tried to start a call"))

    response = TestClient(t.app).post("/trigger/notebook", files={"file": ("page.png", b"fixture", "image/png")},
                                      data={"dry_run": "true"}, headers={"X-API-Key": "test-trigger-key"})
    assert response.status_code == 200
    body = response.json()
    assert "call_queue" in body
    queue = body["call_queue"]
    assert [(r["rank"], r["customer_id"]) for r in queue] == [
        (1, "late"), (2, "also-late"), (3, "today"), (4, "tomorrow")]
    assert queue[0]["name"] == "Meera"
    assert queue[0]["outstanding_amount"] == 800
    assert queue[0]["due_date"] == "2026-11-16"
    assert [r["customer_id"] for r in body["results"]] == [r["customer_id"] for r in rows]
    assert queue[0]["reason"] == body["results"][3]["reason"]


def test_same_borrower_is_called_once_per_day(monkeypatch):
    sent = []

    class Ok:
        ok = True

    monkeypatch.setattr(t.requests, "post", lambda url, json, headers, timeout: sent.append(json) or Ok())
    assert t.check_and_call(row(), dry_run=False, now=NOON)["status"] == "call_triggered"
    assert t.check_and_call(row(), dry_run=False, now=NOON)["status"] == "skipped"
    assert len(sent) == 1
    assert sent[0]["phone_number"] == "9876543210"


def test_relay_webhook_receives_customer_fields_and_call_mapping(monkeypatch):
    monkeypatch.setattr(t, "CALL_API_URL", "https://sandbox.cashfree.com/relay/inbound/webhook/example")
    sent = []

    class Ok:
        ok = True

    monkeypatch.setattr(t.requests, "post", lambda url, json, headers, timeout: sent.append(json) or Ok())
    assert t.check_and_call(row(), dry_run=False, now=NOON)["status"] == "call_triggered"

    assert set(sent[0]) == {"data"}
    payload = sent[0]["data"]
    customer_fields = {key: payload[key] for key in row()}
    assert customer_fields == {**row(), "language": "kn-IN", "interest_rate": 2.0}
    assert payload["event"] == "start_collection_call"
    assert payload["request_id"] == payload["trigger_id"]
    assert payload["phone"] == "+919876543210"
    assert payload["preferred_language"] == "Kannada"
    assert payload["amount_due"] == 4500
    assert payload["link_id"] == f"emi-{payload['installment_id']}"


def test_wrong_api_key_is_rejected():
    client = TestClient(t.app)
    body = {"name": "Ramesh Kumar", "phone_number": "9876543210",
            "due_date": "2026-11-20", "outstanding_amount": 4500}
    assert client.post("/trigger/call?dry_run=true", json=body,
                       headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/trigger/call?dry_run=true", json=body,
                       headers={"X-API-Key": "test-trigger-key"}).status_code == 200
