# Webhook contract

There are three event sources. The borrower dashboard or queue requests an outbound call. Sarvam reports a conversation outcome. Cashfree reports checkout changes. Use the stored installment record as the source of truth for amount, currency, link ownership, and contact details.

## Start a call

Submit a customer record to `POST /trigger/call` with the trigger API key. The notebook endpoint accepts the same fields after extraction.

| Field | Format |
| --- | --- |
| `customer_id` | Customer reference |
| `name` | Customer name |
| `phone_number` | Indian mobile number |
| `email` | Email address, or an empty string if unavailable |
| `language` | Language name such as `Kannada`, or its locale code `kn-IN` |
| `lending_date` | Loan origination date, preferably `YYYY-MM-DD` |
| `due_date` | Payment due date, preferably `YYYY-MM-DD` |
| `outstanding_amount` | Outstanding amount in INR |
| `principal_amount` | Original principal in INR |
| `interest_rate` | Percentage, such as `2` for 2% |

When `CALL_API_URL` points to a Cashfree Relay sandbox inbound webhook, the trigger API forwards these fields inside the outer `data` object and sets `data.event` to `start_collection_call`. It adds `request_id`, an installment reference derived from the customer and due date, and the fields used by the current Relay bindings, including E.164 `phone` and an Indus language name in `preferred_language`. Both the live webhook POST and the Relay test editor use the `{"data": {...}}` envelope shown in the checked-in examples.

## Act on a borrower request

An Indus API tool can pass a request while the borrower is still on the call. If the Relay webhook acknowledges asynchronously, treat the result as queued and confirm creation separately before saying a link was sent. Sarvam's outbound completion webhook provides `attempt_id` and `final_agent_variables` for later reconciliation. [Indus HTTPS tools](https://docs.sarvam.ai/voice-agents/build/tools/https-tool) · [Indus completion webhook](https://docs.sarvam.ai/voice-agents/api/instant-outbound/webhook-payload)

| Request | Relay behavior |
| --- | --- |
| `create_payment_link` | Resolve the installment, reuse its existing link if available, and create one in the sandbox if needed. |
| `fetch_payment_status` | Look up the stored link and return Cashfree's current status. |
| `already_paid` | Pause outreach and flag the installment for reconciliation. |
| `callback_requested` | Record the requested callback time and defer the queue entry. |

The checked-in examples are Relay test editor samples. They use the `data` envelope displayed in Relay's data selector. The borrower name and amount are synthetic, and the recipient value is a placeholder.

For the local demo, the lender or a trusted server can send these outcomes to the trigger API with `X-API-Key`: `POST /queue/{installment_id}/already-paid` (no body) or `POST /queue/{installment_id}/callback` with `{"callback_at":"2027-01-05T11:00:00+05:30"}` (use a future date). A claim pauses calls but cannot mark an installment paid. These endpoints are not automatically subscribed to Relay events.

## Confirm checkout

The trigger API accepts **`POST /webhooks/cashfree/payment-link`** from Cashfree PG sandbox. On the server, set `CASHFREE_PG_CLIENT_ID` and `CASHFREE_PG_CLIENT_SECRET` for the same sandbox merchant that owns the links. Cashfree signs the notification with this PG secret; the lender's `X-API-Key` is not webhook authentication. The receiver uses the same `COLLECTIONS_DB` as the lender queue.

1. **Authenticate the raw delivery.** The signed message is the `x-webhook-timestamp` header bytes followed immediately by the exact body bytes. Compare `x-webhook-signature` to `Base64(HMAC-SHA256(PG secret, signed message))` before parsing. [Cashfree signature specification](https://www.cashfree.com/docs/payments/online/webhooks/signature-verification)
2. **Match the installment.** The [Payment Links schema](https://www.cashfree.com/docs/api-reference/payments/latest/payment-links/webhooks) shows top-level `type: PAYMENT_LINK_EVENT` with `data.link_id` (merchant ID) and `data.link_status`: `PARTIALLY_PAID`, `PAID`, `EXPIRED` or `CANCELLED`. The page illustrates JSON and also mentions form data without specifying its field encoding. The receiver accepts the JSON envelope, or URL-encoded/multipart fields `type` and `data` where `data` is JSON text. It ignores unrelated signed types, statuses and unknown links with HTTP 200.
3. **Fetch before crediting.** For a registered `emi-<installment_id>`, the server fetches the stored link from Cashfree sandbox and checks link ID, owner phone, INR currency and original amount. Only the authenticated lookup's cumulative paise are recorded. Delivery amounts, transaction IDs and URLs are never used. Repeated or out-of-order notifications cannot double-credit or reduce the paid total. A partial leaves the remainder in the queue; a full payment ends outreach.

HTTP **200** acknowledges a committed update or an ignored event. Invalid signatures get **401**, malformed signed envelopes **400**, and bodies over 256 KiB **413**. An unavailable or mismatched lookup, database failure, or a full notice before the lookup confirms full payment gets **503** so [Cashfree can retry](https://www.cashfree.com/docs/payments/online/webhooks/overview#retry-webhooks-policy). The lender can still use `POST /queue/{installment_id}/refresh` if delivery or retries do not complete.

**Verification limit:** `python -m pytest -q calltrigger-api/test_cashfree_webhook.py` exercises signed fixtures against SQLite and a simulated Cashfree HTTP response. No dashboard subscription, real sandbox delivery or external transaction was verified. Automatic delivery requires the sandbox to send Payment Link events to the reachable HTTPS endpoint.
