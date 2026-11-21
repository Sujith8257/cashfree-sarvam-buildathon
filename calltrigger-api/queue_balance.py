"""Pure installment identity, amount and outreach rules for the lender queue."""

import hashlib
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

_IST = timezone(timedelta(hours=5, minutes=30), "IST")
_CURRENCY = r"(?:₹|INR|Rs\.?)"
_SIGNED_RUPEES = re.compile(
    r"([+-]?)\s*((?:\d+|\d{1,2}(?:,\d{2})*,\d{3}|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?)"
)


def installment_id(customer_id: str, phone_number: str, due_date: str) -> str:
    """Use the same borrower and normalized notebook date as the Relay payload."""
    text = "".join(str(int(c)) if c.isdecimal() else c for c in due_date.strip())
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            due = datetime.strptime(text, fmt).date()
        except ValueError:
            continue
        ref = f"{customer_id or phone_number}:{due.isoformat()}"
        return hashlib.sha256(ref.encode()).hexdigest()[:24]
    raise ValueError("Invalid installment due date")


def to_paise(value) -> int:
    """Convert a whole INR amount to signed integer paise, without rounding."""
    if isinstance(value, str):
        text = value.strip().replace("−", "-")
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1].strip()
        text = re.sub(rf"^([+-]?)\s*{_CURRENCY}\s*", r"\1", text, flags=re.I)
        text = re.sub(rf"\s*(?:{_CURRENCY}|/-)$", "", text, flags=re.I)
        match = _SIGNED_RUPEES.fullmatch(text)
        if not match:
            raise ValueError("Expected a single INR amount with at most two decimal places")
        value = match[1] + match[2].replace(",", "")
    elif isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Expected a numeric INR amount")

    amount = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    if not amount.is_finite() or amount.as_tuple().exponent < -2:
        raise ValueError("Expected a finite INR amount with at most two decimal places")
    # Integer arithmetic keeps large balances exact even under a low Decimal precision.
    numerator, denominator = amount.as_integer_ratio()
    return numerator * 100 // denominator


def outreach_state(record: dict, now: datetime) -> tuple[str | None, str | None]:
    """Return an outreach hold or, if normal call gates apply, optional context."""
    amount, paid = record["amount_paise"], record["paid_paise"]
    if 0 < amount <= paid:
        return "paid", "Full payment verified."
    if record["claimed_paid"]:
        return "payment_hold", "Borrower reports paying in full; full payment is not verified."

    reasons = []
    if record["callback_at"] is not None:
        callback = datetime.fromisoformat(record["callback_at"])
        if callback.utcoffset() is None or now.utcoffset() is None:
            raise ValueError("Callback and current time must include a timezone")
        if now < callback:
            return "callback_wait", f"Callback requested for {callback.astimezone(_IST):%Y-%m-%d %H:%M %Z}."
        reasons.append("Requested callback time has arrived.")
    if 0 < paid < amount:
        rupees, paise = divmod(amount - paid, 100)
        reasons.append(f"Partial payment verified; ₹{rupees}.{paise:02d} remaining.")
    return None, " ".join(reasons) or None
