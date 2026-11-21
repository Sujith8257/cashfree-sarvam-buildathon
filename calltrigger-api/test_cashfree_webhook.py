import base64
import hmac
import json
import sqlite3
from unittest.mock import Mock

import httpx
import pytest
import requests
from fastapi.testclient import TestClient

import payment_store as store


PATH = "/webhooks/cashfree/payment-link"
IID = "0123456789abcdef01234567"
LINK = f"emi-{IID}"
PROFILE = {"customer_id": "fixture", "name": "Fixture", "phone_number": "9000000000", "due_date": "2026-11-20"}
SECRET = "offline-pg-secret"
TIMESTAMP = "1795242600000"


@pytest.fixture
def provider(monkeypatch):
    send = Mock(side_effect=AssertionError("Unexpected outbound request"))
    monkeypatch.setattr(requests.Session, "send", lambda self, req, **kw: send(req))
    return send


@pytest.fixture
def client(tmp_path, monkeypatch, provider):
    monkeypatch.setenv("TRIGGER_API_KEY", "test-trigger-key")
    monkeypatch.setenv("CASHFREE_PG_CLIENT_SECRET", SECRET)
    monkeypatch.setenv("CASHFREE_PG_CLIENT_ID", "offline-pg-client")
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "queue.sqlite3"))
    from trigger_api import app

    store.register(IID, PROFILE, 10029)
    with TestClient(app) as client:
        yield client


def event(link_id=LINK, status="PARTIALLY_PAID", kind="PAYMENT_LINK_EVENT"):
    return {"type": kind, "version": 1, "event_time": "2026-11-21T12:00:00+05:30",
            "data": {"cf_link_id": 101, "link_id": link_id, "link_status": status, "link_currency": "INR",
                     "link_amount": "100.29", "link_amount_paid": "100.29" if status == "PAID" else "49.00",
                     "customer_details": {"customer_phone": "9000000001"},
                     "order": None if status in ("EXPIRED", "CANCELLED") else {
                         "order_id": "fixture-order", "order_amount": "49.00", "transaction_status": "SUCCESS"}}}


def wire(obj):
    return json.dumps(obj, indent=2).encode() + b"\n"


def headers(raw):
    signature = hmac.digest(SECRET.encode(), TIMESTAMP.encode() + raw, "sha256")
    return {"x-webhook-timestamp": TIMESTAMP, "x-webhook-signature": base64.b64encode(signature).decode(),
            "content-type": "application/json"}


def deliver(client, raw):
    return client.post(PATH, content=raw, headers=headers(raw))


def fetched(status="PARTIALLY_PAID", paid="19.99", **changes):
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps({"link_id": LINK, "link_currency": "INR", "link_amount": "100.29",
                                    "link_status": status, "link_amount_paid": paid,
                                    "customer_details": {"customer_phone": PROFILE["phone_number"]}, **changes}).encode()
    return response


def test_signed_notifications_use_only_fetched_cumulative_totals(client, provider):
    partial, full = wire(event()), wire(event(status="PAID"))
    provider.side_effect = [fetched(), fetched(), fetched("PAID", "100.29"), fetched()]
    for body, expected in [(partial, 1999), (partial, 1999), (full, 10029), (partial, 10029)]:
        assert deliver(client, body).status_code == 200
        assert store.get(IID)["paid_paise"] == expected
    for call in provider.call_args_list:
        request, = call.args
        assert (request.method, request.url) == ("GET", f"https://sandbox.cashfree.com/pg/links/{LINK}")
        assert request.headers["x-client-secret"] == SECRET
    queue = client.get("/queue", headers={"X-API-Key": "test-trigger-key"}).json()
    assert queue["call_queue"] == []
    assert [(r["status"], r["outstanding_amount"]) for r in queue["other"]] == [("paid", 0)]


def test_signature_covers_exact_body_and_timestamp_before_parsing(client, provider):
    raw = wire(event())
    valid = headers(raw)
    cases = [(raw, {}), (raw, {"X-API-Key": "test-trigger-key"}),
             (raw, {"x-webhook-signature": valid["x-webhook-signature"]}),
             (raw, {"x-webhook-timestamp": TIMESTAMP}),
             (raw, {**valid, "x-webhook-timestamp": "1795242600001"}),
             (raw.rstrip(), valid), (b"not json", valid)]
    for body, hdr in cases:
        assert client.post(PATH, content=body, headers=hdr).status_code == 401
    provider.assert_not_called()
    assert store.get(IID)["paid_paise"] == 0


def test_unsigned_delivery_does_not_initialize_the_database(client, tmp_path, monkeypatch):
    unopened = tmp_path / "unused.sqlite3"
    monkeypatch.setenv("COLLECTIONS_DB", str(unopened))
    assert client.post(PATH, json=event()).status_code == 401
    assert not unopened.exists()


@pytest.mark.parametrize("raw", [b"{", b"[]", b"{}", wire({"type": "PAYMENT_LINK_EVENT", "data": []}),
                                  wire(event(link_id=None)), wire(event(link_id="")), wire(event(status=None)),
                                  wire(event()).replace(b'"link_id":', b'"link_id":"other", "link_id":')],
                         ids=["json", "list", "missing-type", "data-list", "null-id", "empty-id", "null-status", "duplicate-id"])
def test_signed_malformed_event_is_rejected_without_lookup(client, provider, raw):
    assert deliver(client, raw).status_code == 400
    provider.assert_not_called()
    assert store.get(IID)["paid_paise"] == 0


def test_irrelevant_signed_events_and_unregistered_links_are_acknowledged(client, provider):
    for obj in [event(kind="PAYMENT_SUCCESS_WEBHOOK"), event(status="FUTURE_STATUS"),
                event("shop-other"), event("emi-" + "f" * 24)]:
        obj["data"]["order"] = {"order_id": LINK}
        assert deliver(client, wire(obj)).status_code == 200
    provider.assert_not_called()
    assert [(r["installment_id"], r["paid_paise"]) for r in store.all_installments()] == [(IID, 0)]


@pytest.mark.parametrize("failure", [requests.Timeout("private upstream detail"),
                                     fetched(link_id="emi-other"), fetched(link_currency="USD"),
                                     fetched(customer_details={"customer_phone": "9000000001"})])
def test_failed_lookup_preserves_balance_and_same_delivery_can_retry(client, provider, failure):
    store.record_payment(IID, 123)
    provider.side_effect = [failure, fetched()]
    body = wire(event())
    failed = deliver(client, body)
    assert 500 <= failed.status_code < 600
    assert all(value not in failed.text for value in [SECRET, "private", LINK, PROFILE["phone_number"]])
    assert store.get(IID)["paid_paise"] == 123
    assert deliver(client, body).status_code == 200
    assert store.get(IID)["paid_paise"] == 1999


def test_unconfigured_signing_secret_fails_closed(client, provider, monkeypatch):
    monkeypatch.delenv("CASHFREE_PG_CLIENT_SECRET")
    assert deliver(client, wire(event())).status_code == 503
    provider.assert_not_called()
    assert store.get(IID)["paid_paise"] == 0


def test_ack_waits_for_local_commit(client, provider, monkeypatch):
    def unavailable(*args):
        raise sqlite3.OperationalError("private database detail")

    raw = wire(event())
    provider.side_effect = [fetched(), fetched()]
    with monkeypatch.context() as patch:
        patch.setattr(store, "record_payment", unavailable)
        failed = deliver(client, raw)
    assert failed.status_code == 503 and "private" not in failed.text
    assert store.get(IID)["paid_paise"] == 0
    assert deliver(client, raw).status_code == 200
    assert store.get(IID)["paid_paise"] == 1999


def test_oversized_delivery_is_not_processed(client, provider):
    assert deliver(client, wire(event()) + b" " * (256 * 1024)).status_code == 413
    provider.assert_not_called()
    assert store.get(IID)["paid_paise"] == 0


@pytest.mark.parametrize("encoding", ["urlencoded", "multipart"])
def test_form_envelope_is_verified_before_decoding(client, provider, encoding):
    evt = event(status="EXPIRED")
    form = {"type": evt["type"], "data": json.dumps(evt["data"])}
    kwargs = {"data": form} if encoding == "urlencoded" else {"files": {k: (None, v) for k, v in form.items()}}
    request = httpx.Request("POST", "http://testserver", **kwargs)
    raw = request.read()
    hdr = {**headers(raw), "content-type": request.headers["content-type"]}
    assert client.post(PATH, content=raw.replace(b"EXPIRED", b"CANCELLED"), headers=hdr).status_code == 401
    provider.side_effect = [fetched("EXPIRED", "19.99")]
    assert client.post(PATH, content=raw, headers=hdr).status_code == 200
    assert store.get(IID)["paid_paise"] == 1999


@pytest.mark.parametrize("status,first,second,initial,final", [
    ("PAID", fetched(), fetched("PAID", "100.29"), 1999, 10029),
    ("PARTIALLY_PAID", fetched("ACTIVE", "0"), fetched(), 0, 1999),
])
def test_payment_notice_retries_when_provider_state_lags(client, provider, status, first, second, initial, final):
    provider.side_effect = [first, second]
    raw = wire(event(status=status))
    assert deliver(client, raw).status_code == 503
    assert store.get(IID)["paid_paise"] == initial
    assert deliver(client, raw).status_code == 200
    assert store.get(IID)["paid_paise"] == final
