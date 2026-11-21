import json
from unittest.mock import Mock

import pytest
import requests

from cashfree_status import PaymentLookupError, fetch_paid_paise


LINK = "emi-fixture_01"
PHONE = "9000000000"
TOTAL = 10029


def link(**changes):
    return {"link_id": LINK, "link_currency": "INR", "link_amount": 100.29,
            "link_status": "PAID", "link_amount_paid": 100.29,
            "customer_details": {"customer_phone": f"+91{PHONE}"}, **changes}


def response(body, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return result


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("CASHFREE_PG_CLIENT_ID", "fixture-client")
    monkeypatch.setenv("CASHFREE_PG_CLIENT_SECRET", "fixture-secret")
    send = Mock(side_effect=AssertionError("Unexpected provider request"))
    monkeypatch.setattr(requests.Session, "request",
                        lambda self, method, url, **kw: send(method.upper(), url, **kw))
    return send


def test_uses_one_authenticated_sandbox_get(provider):
    provider.side_effect = [response(link(customer_details={"customer_phone": PHONE}))]
    assert fetch_paid_paise(LINK, TOTAL, f"+91{PHONE}") == TOTAL
    assert provider.call_count == 1
    args, kwargs = provider.call_args
    assert args == ("GET", f"https://sandbox.cashfree.com/pg/links/{LINK}")
    assert kwargs["headers"] == {"x-client-id": "fixture-client", "x-client-secret": "fixture-secret",
                                 "x-api-version": "2025-01-01"}
    assert kwargs["allow_redirects"] is False
    assert 0 < kwargs["timeout"] < float("inf")


@pytest.mark.parametrize("state,paid,want", [
    ("PAID", "100.290", 10029), ("PARTIALLY_PAID", 19.99, 1999), ("ACTIVE", 0, 0),
    ("EXPIRED", 0, 0), ("EXPIRED", "19.99", 1999), ("CANCELLED", 0, 0), ("CANCELLED", 1, 100),
])
def test_returns_only_confirmed_cumulative_paise(provider, state, paid, want):
    provider.side_effect = [response(link(link_status=state, link_amount_paid=paid))]
    amount = fetch_paid_paise(LINK, TOTAL, PHONE)
    assert type(amount) is int and amount == want


@pytest.mark.parametrize("state,paid", [
    ("PAID", 0), ("PAID", 19.99), ("PARTIALLY_PAID", 0), ("PARTIALLY_PAID", 100.29),
    ("ACTIVE", 19.99), ("ACTIVE", 100.29), ("EXPIRED", 100.29), ("CANCELLED", 100.29),
    ("UNKNOWN", 0), ("PARTIALLY_PAID", -1), ("PARTIALLY_PAID", 101),
    ("PARTIALLY_PAID", True), ("PARTIALLY_PAID", "1.001"), ("ACTIVE", None),
])
def test_holds_contradictory_or_unsupported_evidence(provider, state, paid):
    provider.side_effect = [response(link(link_status=state, link_amount_paid=paid))]
    with pytest.raises(PaymentLookupError) as error:
        fetch_paid_paise(LINK, TOTAL, PHONE)
    assert error.value.status_code == 409


@pytest.mark.parametrize("changes", [
    {"link_id": "different-link"}, {"link_amount": 100.28}, {"link_currency": "USD"},
    {"customer_details": {"customer_phone": "9000000001"}},
    {"customer_details": {"customer_phone": f"+44{PHONE}"}}, {"customer_details": {}},
])
def test_rejects_payment_for_the_wrong_installment_or_customer(provider, changes):
    provider.side_effect = [response(link(**changes))]
    with pytest.raises(PaymentLookupError) as error:
        fetch_paid_paise(LINK, TOTAL, PHONE)
    assert error.value.status_code == 409


@pytest.mark.parametrize("field", ["link_amount", "link_amount_paid"])
def test_sub_paise_json_number_cannot_round_into_full_payment(provider, field):
    raw = json.dumps(link(**{field: "AMOUNT"})).replace('"AMOUNT"', "100.2900000000000000000000000000001")
    provider.side_effect = [response(raw.encode())]
    with pytest.raises(PaymentLookupError) as error:
        fetch_paid_paise(LINK, TOTAL, PHONE)
    assert error.value.status_code == 409


@pytest.mark.parametrize("link_id,expected,phone", [
    ("../other?x=1", TOTAL, PHONE), (LINK, 0, PHONE), (LINK, -10, PHONE),
    (LINK, True, PHONE), (LINK, TOTAL, f"+44{PHONE}"),
])
def test_invalid_local_identity_or_amount_never_makes_a_request(provider, link_id, expected, phone):
    with pytest.raises(PaymentLookupError) as error:
        fetch_paid_paise(link_id, expected, phone)
    assert error.value.status_code == 409
    provider.assert_not_called()


@pytest.mark.parametrize("key", ["CASHFREE_PG_CLIENT_ID", "CASHFREE_PG_CLIENT_SECRET"])
def test_missing_credentials_are_unavailable(provider, monkeypatch, key):
    monkeypatch.delenv(key)
    with pytest.raises(PaymentLookupError) as error:
        fetch_paid_paise(LINK, TOTAL, PHONE)
    assert error.value.status_code == 503
    provider.assert_not_called()


@pytest.mark.parametrize("upstream,code", [
    (requests.Timeout("https://private.invalid/fixture-secret"), 504),
    (requests.ConnectionError("https://private.invalid/fixture-secret"), 502),
    (response(link(), 302), 502), (response(b"private provider body", 500), 502),
    (response(b"private provider body"), 502), (response([]), 502),
    (response(json.dumps(link()).replace('"PAID"', '"ACTIVE", "link_status": "PAID"').encode()), 502),
])
def test_upstream_failure_has_safe_detail(provider, upstream, code):
    provider.side_effect = [upstream]
    with pytest.raises(PaymentLookupError) as error:
        fetch_paid_paise(LINK, TOTAL, PHONE)
    assert error.value.status_code == code
    detail = str(error.value)
    assert detail and not any(value in detail for value in ("fixture", "private", "https://", PHONE, LINK))
