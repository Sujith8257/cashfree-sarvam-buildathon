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

## Confirm checkout

Cashfree emits `PAYMENT_LINK_EVENT` with `data.link_id`, `data.link_status`, and `data.link_amount_paid`. Verify the webhook signature where raw request bytes and headers are available, and fetch the link through the authenticated Cashfree connection before updating the tracked installment. Apply status updates idempotently. Treat partial payment as a remaining balance and confirmed full payment as a reason to remove the installment from the outreach queue. [Cashfree payment-link event schema](https://www.cashfree.com/docs/api-reference/payments/latest/payment-links/webhooks)
