import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIRST = {"customer_id": "A", "name": "Test Meera", "phone_number": "9000000001",
         "due_date": "2026-11-18", "outstanding_amount": 1200}
SECOND = {**FIRST, "customer_id": "", "name": "M.", "phone_number": "+91 ९००००००००१", "due_date": "2026-11-19"}
OTHER = {**FIRST, "customer_id": "B", "phone_number": "9000000002"}  # Same display name, different phone.
PAGE = {"file": ("fixture.png", b"mock OCR input", "image/png")}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("TRIGGER_API_KEY", "test-trigger-key")
    import trigger_api
    return trigger_api


@pytest.fixture
def client(tmp_path, monkeypatch, api):
    def reject_network(*args, **kwargs):
        raise AssertionError("Unexpected network I/O")

    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "collection.sqlite3"))
    monkeypatch.setattr(api, "now_ist", lambda: datetime.fromisoformat("2026-11-21T12:00:00+05:30"))
    monkeypatch.setattr(api, "CALL_API_URL", "https://dispatch.test/call")
    monkeypatch.setattr(api.requests.sessions.Session, "send", reject_network)
    monkeypatch.setattr(api, "read_notebook", lambda *args: [FIRST, SECOND])
    with TestClient(api.app, headers={"X-API-Key": "test-trigger-key"}) as client:
        yield client


def body(response):
    assert response.status_code == 200, response.text
    return response.json()


def typed(client, row=FIRST, dry=True):
    return body(client.post("/trigger/call", params={"dry_run": dry}, json=row))


def stop(client, iid, reason):
    return body(client.post(f"/queue/{iid}/contact-preference", json={"reason": reason}))


@pytest.mark.parametrize("reason", ["no_contact", "hardship"])
def test_registered_phone_stops_both_dispatch_routes_and_previews_across_installments(client, reason):
    iid = typed(client)["installment_id"]
    other_id = typed(client, OTHER)["installment_id"]
    stop(client, iid, reason)

    for dry in (True, False):
        result = typed(client, SECOND, dry=dry)  # A new installment, imported after the stop.
        assert result["status"] == reason
        assert result["paid_amount"] == 0 and result["outstanding_amount"] == 1200
        assert "support" in result["reason"].lower()
        assert any('\u0c80' <= c <= '\u0cff' for c in result["reason"])  # Kannada support copy.
        page = body(client.post("/trigger/notebook", files=PAGE, data={"dry_run": str(dry).lower()}))
        assert page["calls"] == 0
        assert [r["status"] for r in page["results"]] == [reason, reason]
        if dry:
            assert page["call_queue"] == []

    queue = body(client.get("/queue"))
    assert [r["installment_id"] for r in queue["call_queue"]] == [other_id]
    assert {(r["installment_id"], r["status"]) for r in queue["other"]} == {
        (iid, reason), (result["installment_id"], reason)}


def test_no_contact_is_durable_and_cannot_be_weakened_by_later_hardship_or_callback(client, api):
    iid = typed(client)["installment_id"]
    for reason in ("hardship", "no_contact", "no_contact", "hardship"):
        effective = stop(client, iid, reason)
    assert effective["status"] == "no_contact"
    callback = body(client.post(f"/queue/{iid}/callback", json={"callback_at": "2026-11-22T10:00:00+05:30"}))
    assert callback["status"] == "no_contact"

    # A fresh interpreter opens the same database, without any of this process's state.
    read = subprocess.check_output([sys.executable, "-c",
        "import json, trigger_api; print(json.dumps(trigger_api.lender_queue()))"],
        cwd=Path(api.__file__).parent, text=True)
    restarted = json.loads(read)
    assert restarted["call_queue"] == []
    assert [(r["installment_id"], r["status"]) for r in restarted["other"]] == [(iid, "no_contact")]


def test_stops_preserve_paid_and_claim_statuses_and_verified_amounts(client, api):
    paid = typed(client)["installment_id"]
    claim = typed(client, SECOND)["installment_id"]
    api.store.record_payment(paid, 120000)
    body(client.post(f"/queue/{claim}/already-paid"))
    saved = stop(client, paid, "hardship")
    assert saved["status"] == "paid" and "hardship" in saved["reason"].lower()
    held = typed(client, SECOND, dry=False)
    assert held["status"] == "payment_hold" and "hardship" in held["reason"].lower()
    assert (saved["paid_amount"], held["paid_amount"]) == (1200, 0)


def test_live_dispatch_rechecks_a_stop_committed_while_preparing_the_call(client, monkeypatch, api):
    iid = typed(client)["installment_id"]
    monkeypatch.setattr(api, "CALL_API_URL", "https://sandbox.cashfree.com/relay/inbound/webhook/test-only")
    prepare = api.relay_call_payload

    def record_while_preparing(payload):
        stop(client, iid, "no_contact")
        return prepare(payload)

    monkeypatch.setattr(api, "relay_call_payload", record_while_preparing)
    assert typed(client, dry=False)["status"] == "no_contact"


def test_only_authorized_known_installments_can_record_a_supported_reason(client, api):
    iid = typed(client)["installment_id"]
    path = f"/queue/{iid}/contact-preference"
    with TestClient(api.app) as outsider:
        for headers in ({}, {"X-API-Key": "wrong"}):
            assert outsider.post(path, headers=headers, json={"reason": "no_contact"}).status_code in (401, 403)
    assert client.post("/queue/missing/contact-preference", json={"reason": "hardship"}).status_code == 404
    for invalid in ({"reason": "resume"}, {"reason": "no_contact", "phone_number": OTHER["phone_number"]}):
        assert client.post(path, json=invalid).status_code == 422
    assert [r["installment_id"] for r in body(client.get("/queue"))["call_queue"]] == [iid]
