from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext

import pytest

import queue_balance as balance


@pytest.mark.parametrize(("customer_id", "due_date", "expected"), [
    ("C001", "2026-11-20", "ac23c329cad5b383c5052c74"),
    ("C001", "२०/११/२०२६", "ac23c329cad5b383c5052c74"),
    ("", "20.11.2026", "be867fc3ae00b358c7e4f075"),
])
def test_installment_id_matches_existing_relay_reference(customer_id, due_date, expected):
    assert balance.installment_id(customer_id, "9876543210", due_date) == expected


def test_invalid_due_date_cannot_become_a_new_installment():
    with pytest.raises(ValueError):
        balance.installment_id("C001", "9876543210", "31/11/2026")


@pytest.mark.parametrize(("value", "expected"), [
    (0, 0), (1800, 180000), (0.29, 29), (-0.01, -1),
    (Decimal("9007199254740993.01"), 900719925474099301),
    (" ₹ १,२३,४५६.७८ ", 12345678), ("-Rs. 2,000.50", -200050),
    ("INR −0.05", -5), ("(₹1,200.50)", -120050), ("2,500/-", 250000),
    ("+12.3 INR", 1230),
])
def test_to_paise_converts_the_entire_signed_rupee_amount_exactly(value, expected):
    with localcontext(prec=4):
        result = balance.to_paise(value)
    assert type(result) is int
    assert result == expected


@pytest.mark.parametrize("value", [
    None, True, {}, "", "Rs.", "500-700", "₹ 200 to ₹ 300", "100/200", "1,23",
    "12,,345", "500 CR", "500 or 600", "₹-+10", "(-20)", "₹50 USD", "1e3",
    "1.005", -0.001, Decimal("1.230"), Decimal("NaN"), float("inf"), float("-inf"),
])
def test_to_paise_rejects_unclear_or_sub_paise_values(value):
    with pytest.raises(ValueError):
        balance.to_paise(value)


CALLBACK = datetime(2026, 11, 21, 18, 35, tzinfo=timezone.utc)
BEFORE = CALLBACK - timedelta(seconds=1)


def record(**changes):
    return {"amount_paise": 100000, "paid_paise": 0, "claimed_paid": False,
            "callback_at": None, **changes}


@pytest.mark.parametrize("paid", [100000, 100001])
def test_verified_full_or_excess_payment_wins_over_a_claim_and_callback(paid):
    row = record(paid_paise=paid, claimed_paid=True, callback_at=CALLBACK.isoformat())
    status, reason = balance.outreach_state(row, BEFORE)
    assert status == "paid"
    assert "verified" in reason.lower()


@pytest.mark.parametrize(("amount", "paid"), [(100000, 0), (0, 0), (0, 1), (-100, 0), (100000, -1)])
def test_no_outreach_override_without_a_positive_debt_and_verified_payment(amount, paid):
    assert balance.outreach_state(record(amount_paise=amount, paid_paise=paid), BEFORE) == (None, None)


@pytest.mark.parametrize("paid", [0, 24975])
def test_borrower_claim_pauses_outreach_even_if_a_callback_is_scheduled(paid):
    row = record(paid_paise=paid, claimed_paid=True, callback_at=CALLBACK.isoformat())
    status, reason = balance.outreach_state(row, BEFORE)
    assert status == "payment_hold"
    assert "not verified" in reason.lower()


def test_partial_payment_explains_remaining_balance_without_overriding_call_gates():
    status, reason = balance.outreach_state(record(paid_paise=24975), BEFORE)
    assert status is None
    assert "partial" in reason.lower() and "verified" in reason.lower()
    assert "750.25" in reason


@pytest.mark.parametrize("timestamp", ["2026-11-21T18:35:00Z", "2026-11-21T10:35:00-08:00"])
def test_callback_displays_indian_local_date_and_time_and_releases_at_the_instant(timestamp):
    row = record(callback_at=timestamp)
    status, reason = balance.outreach_state(row, BEFORE)
    assert status == "callback_wait"
    assert "2026-11-22" in reason and "00:05" in reason and "IST" in reason

    for now in (CALLBACK, CALLBACK + timedelta(seconds=1)):
        status, reason = balance.outreach_state(row, now)
        assert status is None
        assert "callback" in reason.lower()


def test_elapsed_callback_and_partial_payment_both_explain_eligibility():
    row = record(callback_at=CALLBACK.isoformat(), paid_paise=24975)
    status, reason = balance.outreach_state(row, CALLBACK)
    assert status is None
    assert "callback" in reason.lower() and "partial" in reason.lower()
    assert "750.25" in reason


@pytest.mark.parametrize(("callback_at", "now"), [
    ("2026-11-21T18:35:00", BEFORE), (CALLBACK.isoformat(), BEFORE.replace(tzinfo=None)),
])
def test_callback_never_guesses_the_timezone(callback_at, now):
    with pytest.raises(ValueError):
        balance.outreach_state(record(callback_at=callback_at), now)
