import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

os.environ["SARVAM_API_KEY"] = "test-sarvam-key"
os.environ["TRIGGER_API_KEY"] = "test-trigger-key"
os.environ["CALL_API_URL"] = "http://call-api.test/call"

import pytest
from fastapi.testclient import TestClient

import trigger_api as t


NOON = datetime.fromisoformat("2026-11-23T12:00:00+05:30")
FIRST = {"customer_id": "fixture-A", "name": "Test Borrower A", "phone_number": "9000000001",
         "due_date": "2026-11-18", "outstanding_amount": 1200}
NEXT = {"customer_id": "fixture-B", "name": "Test Borrower B", "phone_number": "9000000002",
        "due_date": "2026-11-23", "outstanding_amount": 825.75}
PAGE = {"file": ("fixture.png", b"mocked notebook page", "image/png")}


@pytest.fixture
def clock(monkeypatch):
    def freeze(at):
        monkeypatch.setattr(t, "now_ist", lambda: at, raising=False)

    freeze(NOON)
    return freeze


@pytest.fixture
def client(tmp_path, monkeypatch, clock):
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "collections.sqlite3"))
    monkeypatch.setattr(t, "read_notebook", lambda *args: [FIRST.copy()])

    def no_network(*args, **kwargs):
        pytest.fail("Unexpected outbound HTTP request during lender queue test")

    monkeypatch.setattr(t.requests.sessions.Session, "send", no_network)
    with TestClient(t.app, headers={"X-API-Key": "test-trigger-key"}) as client:
        yield client


def ok(response):
    request = response.request
    assert response.is_success, f"{request.method} {request.url.path}: {response.status_code} {response.text}"
    return response


def typed_call(client, borrower=FIRST, *, dry_run=True):
    return ok(client.post("/trigger/call", params={"dry_run": dry_run}, json=borrower)).json()


def notebook(client, *, dry_run=True):
    return ok(client.post("/trigger/notebook", files=PAGE, data={"dry_run": str(dry_run).lower()})).json()


def queue(client):
    result = ok(client.get("/queue")).json()
    assert result["as_of"]
    return result


def seed_one(client):
    typed_call(client)
    row, = queue(client)["call_queue"]
    return row["installment_id"]


def assert_balance(row, paid, outstanding):
    assert (row["paid_amount"], row["outstanding_amount"]) == (paid, outstanding)


def test_verified_payments_rerank_the_queue_without_double_counting_or_redialing(client, monkeypatch):
    typed_call(client, NEXT)  # Insert the later due borrower first.
    notebook(client)
    state = queue(client)
    first, following = state["call_queue"]
    assert state["other"] == []
    for row, borrower in ((first, FIRST), (following, NEXT)):
        assert (row["customer_id"], row["name"], row["due_date"]) == (
            borrower["customer_id"], borrower["name"], borrower["due_date"])
        assert row["installment_id"] and row["status"] and row["reason"]
        assert_balance(row, 0, borrower["outstanding_amount"])
    iid = first["installment_id"]
    assert iid != following["installment_id"]

    verified_paise = 50_000

    def lookup(link_id, expected_paise, phone_number):
        assert link_id == f"emi-{iid}"
        assert expected_paise == 120_000  # Link face value, even on the second lookup.
        assert phone_number.removeprefix("+91") == FIRST["phone_number"]
        return verified_paise

    monkeypatch.setattr(t.cashfree_status, "fetch_paid_paise", lookup)
    for _ in range(2):
        ok(client.post(f"/queue/{iid}/refresh"))
        partial = queue(client)["call_queue"][0]
        assert partial["installment_id"] == iid
        assert partial["status"] != "paid"
        assert_balance(partial, 500, 700)

    notebook(client)  # The original page still says INR 1,200.
    assert_balance(queue(client)["call_queue"][0], 500, 700)
    verified_paise = 120_000
    ok(client.post(f"/queue/{iid}/refresh"))

    def assert_settled():
        state = queue(client)
        next_up, = state["call_queue"]
        assert next_up["installment_id"] == following["installment_id"]
        assert_balance(next_up, 0, 825.75)
        paid, = state["other"]
        assert (paid["installment_id"], paid["status"]) == (iid, "paid")
        assert_balance(paid, 1200, 0)

    assert_settled()
    assert typed_call(client, dry_run=False)["status"] != "call_triggered"
    assert notebook(client, dry_run=False)["calls"] == 0
    assert_settled()


def test_already_paid_claim_pauses_outreach_without_crediting_money(client):
    iid = seed_one(client)
    ok(client.post(f"/queue/{iid}/already-paid"))
    assert typed_call(client, dry_run=False)["status"] != "call_triggered"
    state = queue(client)
    assert state["call_queue"] == []
    held, = state["other"]
    assert held["installment_id"] == iid and held["status"] != "paid" and held["reason"]
    assert_balance(held, 0, 1200)


def test_callback_rejoins_at_its_instant_and_only_during_ist_calling_hours(client, clock, monkeypatch):
    iid = seed_one(client)
    due = NOON.replace(hour=14)
    path = f"/queue/{iid}/callback"
    naive = client.post(path, json={"callback_at": due.replace(tzinfo=None).isoformat()})
    assert naive.status_code in (400, 422)
    assert [r["installment_id"] for r in queue(client)["call_queue"]] == [iid]
    ok(client.post(path, json={"callback_at": due.astimezone(timezone.utc).isoformat()}))
    tomorrow = NOON + timedelta(days=1)
    for moment, eligible in ((due - timedelta(seconds=1), False), (due, True),
                             (NOON.replace(hour=19), False), (tomorrow.replace(hour=7, minute=59), False),
                             (tomorrow.replace(hour=8), True)):
        clock(moment)
        state = queue(client)
        assert [r["installment_id"] for r in state["call_queue"]] == ([iid] if eligible else []), moment
        if not eligible:
            held, = state["other"]
            assert held["installment_id"] == iid
            assert_balance(held, 0, 1200)
            assert typed_call(client, dry_run=False)["status"] != "call_triggered"

    dispatch = Mock(return_value=Mock(status_code=200))
    monkeypatch.setattr(t.requests, "post", dispatch)
    assert typed_call(client, dry_run=False)["status"] == "call_triggered"
    assert dispatch.call_count == 1
    assert dispatch.call_args.kwargs["json"]["phone_number"] == FIRST["phone_number"]


def test_untrusted_refresh_cannot_overwrite_a_verified_partial_balance(client, monkeypatch):
    iid = seed_one(client)

    def verified(link_id, expected_paise, phone_number):
        return 50_000 if link_id == f"emi-{iid}" else 120_000

    lookup = Mock(side_effect=verified)
    monkeypatch.setattr(t.cashfree_status, "fetch_paid_paise", lookup)
    path = f"/queue/{iid}/refresh"
    ok(client.post(path))
    assert_balance(queue(client)["call_queue"][0], 500, 700)

    forged = client.post(path, json={"link_id": "emi-another-installment", "link_status": "PAID",
                                     "link_amount_paid": 1200, "paid_amount": 1200, "paid_paise": 120_000})
    # A body may be rejected or ignored; neither is a payment confirmation.
    assert forged.is_success or forged.status_code in (400, 422)
    assert_balance(queue(client)["call_queue"][0], 500, 700)

    lookup.side_effect = t.cashfree_status.PaymentLookupError(409, "payment link belongs to another borrower")
    rejected = client.post(path)
    assert rejected.status_code == 409
    state = queue(client)
    saved, = state["call_queue"] + state["other"]
    assert saved["installment_id"] == iid and saved["status"] != "paid"
    assert_balance(saved, 500, 700)


def queue_actions(iid):
    return [(f"/queue/{iid}/refresh", {}), (f"/queue/{iid}/already-paid", {}),
            (f"/queue/{iid}/callback", {"json": {"callback_at": (NOON + timedelta(hours=1)).isoformat()}})]


def test_unknown_installment_actions_return_404_without_changing_known_debt(client):
    iid = seed_one(client)
    before = queue(client)
    unknown = iid[:-1] + ("1" if iid.endswith("0") else "0")
    for path, kwargs in queue_actions(unknown):
        assert client.post(path, **kwargs).status_code == 404, path
    assert queue(client) == before


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}], ids=["missing-key", "wrong-key"])
def test_unauthorized_requests_cannot_read_or_mutate_the_queue(client, headers, monkeypatch):
    iid = seed_one(client)
    before = queue(client)
    monkeypatch.setattr(t, "read_notebook", lambda *args: [NEXT.copy()])
    with TestClient(t.app, headers=headers) as outsider:
        assert outsider.get("/queue").status_code in (401, 403)
        imports = [("/trigger/call?dry_run=true", {"json": NEXT}),
                   ("/trigger/notebook", {"files": PAGE, "data": {"dry_run": "true"}})]
        for path, kwargs in queue_actions(iid) + imports:
            assert outsider.post(path, **kwargs).status_code in (401, 403), path
    assert queue(client) == before
