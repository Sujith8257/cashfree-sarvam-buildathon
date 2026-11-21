import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ["TRIGGER_API_KEY"] = "test-trigger-key"

import pytest
from fastapi.testclient import TestClient

import trigger_api as api


NOON = datetime.fromisoformat("2026-11-23T12:00:00+05:30")
DEADLINE = "2026-11-23T08:30:00Z"  # 14:00 IST
BORROWER = {"customer_id": "promise-fixture", "name": "Demo Borrower", "phone_number": "9000000001",
            "due_date": "2026-11-20", "outstanding_amount": 1200}


@pytest.fixture
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "demo.sqlite3"))
    monkeypatch.setattr(api, "now_ist", lambda: NOON)
    monkeypatch.setattr(api.requests.sessions.Session, "send", lambda *a, **kw: pytest.fail("Outbound HTTP"))
    with TestClient(api.app, headers={"X-API-Key": "test-trigger-key"}) as client:
        result = client.post("/trigger/call?dry_run=true", json=BORROWER)
        assert result.status_code == 200
        yield client, result.json()["installment_id"]


def promise(client, iid, amount="250.25", at=DEADLINE):
    return client.post(f"/queue/{iid}/promise", json={"amount": amount, "promise_at": at})


def verified(client, iid, monkeypatch, cumulative_paise):
    monkeypatch.setattr(api.cashfree_status, "fetch_paid_paise", lambda *_: cumulative_paise)
    response = client.post(f"/queue/{iid}/refresh")
    assert response.status_code == 200
    return response.json()


def test_earlier_partial_and_retried_promise_do_not_count_as_new_money(demo, monkeypatch):
    client, iid = demo
    verified(client, iid, monkeypatch, 50_000)
    response = promise(client, iid)
    assert response.status_code == 200, response.text
    row = response.json()
    assert (row["status"], row["paid_amount"], row["outstanding_amount"], row["callback_at"]) == (
        "promise_wait", 500, 700, None)
    assert "250.25" in row["reason"] and "2026-11-23 14:00 IST" in row["reason"]
    assert client.get("/queue").json()["call_queue"] == []
    assert client.post("/trigger/call", json=BORROWER).json()["status"] == "promise_wait"

    assert verified(client, iid, monkeypatch, 65_000)["status"] == "promise_wait"
    assert promise(client, iid, at="2026-11-23T14:00:00+05:30").status_code == 200
    assert promise(client, iid, at="2026-11-23T12:01:00+05:30").status_code == 409
    row = verified(client, iid, monkeypatch, 75_025)
    assert row["status"] == "would_call" and "kept" in row["reason"].lower()
    assert row["outstanding_amount"] == 449.75 and "449.75" in row["reason"]

    # Even a second, smaller promise starts from the new cumulative verified total.
    assert promise(client, iid, amount=100).json()["status"] == "promise_wait"
    monkeypatch.setattr(api, "now_ist", lambda: NOON.replace(hour=14))
    row, = client.get("/queue").json()["call_queue"]
    assert "lapsed promise" in row["reason"].lower() and row["outstanding_amount"] == 449.75


def test_shortfall_of_one_paisa_rejoins_ranked_queue_only_at_deadline(demo, monkeypatch):
    client, iid = demo
    other = client.post("/trigger/call?dry_run=true", json={**BORROWER, "due_date": "2026-11-22"}).json()
    assert promise(client, iid, amount=250.25).status_code == 200
    verified(client, iid, monkeypatch, 25_024)
    due = NOON.replace(hour=14)
    monkeypatch.setattr(api, "now_ist", lambda: due - timedelta(microseconds=1))
    assert [r["installment_id"] for r in client.get("/queue").json()["call_queue"]] == [other["installment_id"]]
    monkeypatch.setattr(api, "now_ist", lambda: due)
    first, second = client.get("/queue").json()["call_queue"]
    assert (first["installment_id"], first["rank"], second["installment_id"]) == (iid, 1, other["installment_id"])
    assert "lapsed promise" in first["reason"].lower() and "250.24" in first["reason"]
    assert first["outstanding_amount"] == 949.76
    paid = verified(client, iid, monkeypatch, 120_000)
    assert paid["status"] == "paid" and paid["outstanding_amount"] == 0
    assert promise(client, iid, at="2026-11-24T12:00:00+05:30").status_code == 422


def test_local_deadline_outside_call_hours_and_claim_callback_guards(demo, monkeypatch):
    client, iid = demo
    assert promise(client, iid, at="2026-11-23T18:35:00Z").status_code == 200  # 00:05 IST next day
    held, = client.get("/queue").json()["other"]
    assert "2026-11-24 00:05 IST" in held["reason"]
    after = NOON.replace(day=24, hour=0, minute=5)
    monkeypatch.setattr(api, "now_ist", lambda: after)
    blocked = client.post("/trigger/call", json=BORROWER).json()
    assert blocked["status"] == "blocked" and "calling hours" in blocked["reason"]
    monkeypatch.setattr(api, "now_ist", lambda: after.replace(hour=8))
    callback = client.post(f"/queue/{iid}/callback", json={"callback_at": "2026-11-24T10:00:00+05:30"}).json()
    assert callback["status"] == "callback_wait" and "callback" in callback["reason"].lower()
    assert client.post("/trigger/call", json=BORROWER).json()["status"] == "callback_wait"
    assert client.post(f"/queue/{iid}/already-paid").json()["status"] == "payment_hold"
    assert client.post("/trigger/call", json=BORROWER).json()["status"] == "payment_hold"
    assert verified(client, iid, monkeypatch, 120_000)["status"] == "paid"


@pytest.mark.parametrize(("amount", "at"), [
    (0, DEADLINE), (-1, DEADLINE), (True, DEADLINE), ("0.001", DEADLINE), ("250 USD", DEADLINE),
    ("700.01", DEADLINE), (1, "2026-11-23"), (1, "2026-11-23T14:00:00"), (1, "2026-02-30T14:00:00Z"),
    (1, "2026-11-23T06:30:00Z"), (1, "2026-11-23T06:29:59Z"), (1, 2_000_000_000),
])
def test_invalid_promises_preserve_the_remaining_balance(demo, monkeypatch, amount, at):
    client, iid = demo
    verified(client, iid, monkeypatch, 50_000)
    before = client.get("/queue").json()
    assert promise(client, iid, amount, at).status_code == 422
    assert client.get("/queue").json() == before


def test_action_requires_key_and_known_installment_and_cannot_set_paid_baseline(demo):
    client, iid = demo
    before = client.get("/queue").json()
    for headers in ({}, {"X-API-Key": "wrong"}):
        with TestClient(api.app, headers=headers) as outsider:
            assert promise(outsider, iid).status_code in (401, 403)
    assert promise(client, "unknown-installment").status_code == 404
    forged = client.post(f"/queue/{iid}/promise", json={"amount": 100, "promise_at": DEADLINE,
                                                       "baseline_paid_paise": 0, "paid_paise": 120_000})
    assert forged.status_code == 422
    assert client.get("/queue").json() == before


def test_new_process_can_read_the_signed_terms_and_baseline(demo, monkeypatch):
    client, iid = demo
    verified(client, iid, monkeypatch, 50_000)
    assert promise(client, iid).status_code == 200
    verified(client, iid, monkeypatch, 65_000)
    output = subprocess.check_output([
        sys.executable, "-c", "import json, sys, trigger_api as t; from datetime import datetime; "
        "print(json.dumps(t.queue_entry(t.store.get(sys.argv[1]), datetime.fromisoformat(sys.argv[2]))))",
        iid, NOON.isoformat(),
    ], cwd=Path(api.__file__).parent, text=True)
    row = json.loads(output)
    assert row["status"] == "promise_wait"
    assert row["promise"] == {"promise_at": "2026-11-23T14:00:00+05:30", "promised_paise": 25_025,
                              "baseline_paid_paise": 50_000}
    assert row["paid_amount"] == 650 and row["outstanding_amount"] == 550


def test_promise_preserves_an_independent_receipt_hold_even_after_deadline(demo, monkeypatch):
    client, iid = demo
    # Receipt review can supply a separate hold in the shared outreach decision.
    monkeypatch.setattr(api, "outreach_state", lambda *_: ("receipt_hold", "Receipt under review."))
    row = promise(client, iid).json()
    assert row["status"] == "receipt_hold" and "receipt" in row["reason"].lower()
    monkeypatch.setattr(api, "now_ist", lambda: NOON.replace(hour=15))
    assert client.get("/queue").json()["call_queue"] == []
    row = client.post("/trigger/call", json=BORROWER).json()
    assert row["status"] == "receipt_hold" and "receipt" in row["reason"].lower()


def test_ist_deadline_is_independent_of_clock_offset_and_shows_nonzero_seconds(demo, monkeypatch):
    client, iid = demo
    monkeypatch.setattr(api, "now_ist", lambda: NOON.astimezone(timezone.utc))
    row = promise(client, iid, at="2026-11-23T08:30:59Z").json()
    assert row["promise"]["promise_at"] == "2026-11-23T14:00:59+05:30"
    assert "14:00:59 IST" in row["reason"]
