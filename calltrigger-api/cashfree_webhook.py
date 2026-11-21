"""Reconcile a stored installment after an authenticated Cashfree PG notification."""
import base64
import hmac
import json
import os
import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

import cashfree_status
import payment_store as store


router = APIRouter()
EVENT = "PAYMENT_LINK_EVENT"
FORM_TYPES = ("application/x-www-form-urlencoded", "multipart/form-data")
MAX_BODY = 256 * 1024


async def _verified_body(request):
    secret = os.getenv("CASHFREE_PG_CLIENT_SECRET", "").strip()
    if not secret:
        raise HTTPException(503, "Payment webhook is not configured.")
    timestamps = request.headers.getlist("x-webhook-timestamp")
    signatures = request.headers.getlist("x-webhook-signature")
    if (len(timestamps) != 1 or not re.fullmatch(r"[0-9]+", timestamps[0])
            or len(signatures) != 1 or not signatures[0]):
        raise HTTPException(401, "Invalid webhook signature.")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            raise HTTPException(413, "Webhook body too large.")
        body.extend(chunk)
    mac = hmac.digest(secret.encode(), timestamps[0].encode("ascii") + body, "sha256")
    if not hmac.compare_digest(base64.b64encode(mac), signatures[0].encode("latin-1")):
        raise HTTPException(401, "Invalid webhook signature.")
    return body


async def _verified_event(request: Request):
    body = await _verified_body(request)
    media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
    try:
        if media_type in FORM_TYPES and not body.lstrip().startswith(b"{"):
            # Give the form parser the already bounded, signed bytes; never spool uploads.
            async def receive():
                return {"type": "http.request", "body": bytes(body), "more_body": False}

            async with Request(request.scope, receive).form(max_files=0) as fields:
                event = cashfree_status.unique_fields(fields.multi_items())
            if event.get("type") == EVENT:
                event["data"] = json.loads(event.get("data", ""), object_pairs_hook=cashfree_status.unique_fields)
        else:
            event = json.loads(body, object_pairs_hook=cashfree_status.unique_fields)

        if not isinstance(event, dict) or not isinstance(event.get("type"), str) or not event["type"].strip():
            raise ValueError
        if event["type"] != EVENT:
            return None
        data = event.get("data")
        if not isinstance(data, dict):
            raise ValueError
        link_id, status = data.get("link_id"), data.get("link_status")
        if not all(isinstance(value, str) and value.strip() for value in (link_id, status)):
            raise ValueError
        if status not in ("PAID", "PARTIALLY_PAID", "EXPIRED", "CANCELLED"):
            return None
        return link_id, status
    except (ValueError, RecursionError, StarletteHTTPException):
        raise HTTPException(400, "Malformed payment webhook.") from None


@router.post("/webhooks/cashfree/payment-link", response_class=Response)
def payment_link(event=Depends(_verified_event)):
    """Acknowledge after the blocking sandbox lookup and SQLite commit finish in a worker thread."""
    if event is None:
        return
    link_id, notified_status = event
    match = re.fullmatch(r"emi-([A-Za-z0-9_-]+)", link_id)
    if not match:
        return
    try:
        record = store.get(match[1])
        if record is None or record["link_id"] != link_id:
            return
        paid = cashfree_status.fetch_paid_paise(record["link_id"], record["amount_paise"], record["phone_number"])
        saved = store.record_payment(record["installment_id"], paid)
    except (cashfree_status.PaymentLookupError, sqlite3.Error):
        raise HTTPException(503, "Payment reconciliation unavailable. Retry delivery.") from None

    # A signed status can prompt a retry, but it cannot confirm an amount.
    if ((notified_status == "PAID" and saved["paid_paise"] < saved["amount_paise"])
            or (notified_status == "PARTIALLY_PAID" and saved["paid_paise"] == 0)):
        raise HTTPException(503, "Payment not yet confirmed. Retry delivery.")
