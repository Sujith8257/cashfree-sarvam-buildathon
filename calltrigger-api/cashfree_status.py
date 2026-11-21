"""Read confirmed cumulative payments from a Cashfree sandbox payment link."""

import os
import re
from decimal import Decimal, DecimalException

import requests


class PaymentLookupError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _phone(value):
    if isinstance(value, str):
        national = value.removeprefix("+91")
        if re.fullmatch(r"[0-9]{10}", national):
            return national
    return None


def _unique_fields(pairs):
    fields = dict(pairs)
    if len(fields) != len(pairs):
        raise ValueError("Duplicate JSON field")
    return fields


def _paise(value):
    try:
        if type(value) not in (int, str, Decimal):
            raise ValueError
        if isinstance(value, str) and not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            raise ValueError
        rupees = Decimal(value)
        if not rupees.is_finite() or rupees < 0 or rupees != rupees.quantize(Decimal("0.01")):
            raise ValueError
        return int(rupees * 100)
    except (ValueError, DecimalException):
        raise PaymentLookupError(409, "Payment link contains an invalid amount.") from None


def fetch_paid_paise(link_id: str, expected_paise: int, phone_number: str) -> int:
    """Return the matched link's confirmed paise, or raise if it cannot be verified."""
    phone = _phone(phone_number)
    if (not isinstance(link_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", link_id)
            or type(expected_paise) is not int or expected_paise <= 0 or phone is None):
        raise PaymentLookupError(409, "Invalid installment payment reference.")

    client_id = os.getenv("CASHFREE_PG_CLIENT_ID", "").strip()
    secret = os.getenv("CASHFREE_PG_CLIENT_SECRET", "").strip()
    if not client_id or not secret:
        raise PaymentLookupError(503, "Payment lookup is not configured.")

    try:
        response = requests.get(
            f"https://sandbox.cashfree.com/pg/links/{link_id}",
            headers={"x-client-id": client_id, "x-client-secret": secret, "x-api-version": "2025-01-01"},
            allow_redirects=False, timeout=5,
        )
    except requests.Timeout:
        raise PaymentLookupError(504, "Payment lookup timed out.") from None
    except requests.RequestException:
        raise PaymentLookupError(502, "Payment provider is unavailable.") from None
    if response.status_code != 200:
        raise PaymentLookupError(502, "Payment provider did not return the link.")

    try:
        data = response.json(parse_float=Decimal, object_pairs_hook=_unique_fields)
        if not isinstance(data, dict):
            raise ValueError
    except (ValueError, DecimalException, RecursionError):
        raise PaymentLookupError(502, "Unreadable payment provider response.") from None

    customer = data.get("customer_details")
    if (data.get("link_id") != link_id or data.get("link_currency") != "INR"
            or not isinstance(customer, dict) or _phone(customer.get("customer_phone")) != phone
            or _paise(data.get("link_amount")) != expected_paise):
        raise PaymentLookupError(409, "Payment link does not match this installment.")

    paid = _paise(data.get("link_amount_paid"))
    status = data.get("link_status")
    if ((status == "PAID" and paid == expected_paise)
            or (status == "PARTIALLY_PAID" and 0 < paid < expected_paise)
            or (status == "ACTIVE" and paid == 0)
            or (status in ("EXPIRED", "CANCELLED") and paid < expected_paise)):
        return paid
    raise PaymentLookupError(409, "Payment link status and amount could not be confirmed.")
