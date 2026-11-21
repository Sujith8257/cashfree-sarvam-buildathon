# Webhook contract

There are three event sources. The borrower dashboard or queue requests an outbound call. Sarvam reports a conversation outcome. Cashfree reports checkout changes. Use the stored installment record as the source of truth for amount, currency, link ownership, and contact details.

## Start a call

Set `event` to `start_collection_call`. Include a unique `request_id`, the borrower and installment IDs, and the synthetic profile fields shown in the example file. Use an E.164 test number and a language supported by the committed Indus agent. Resolve the starting language from the profile, and use the request ID to avoid duplicate calls.

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
