# Cashfree × Sarvam Buildathon

A sandbox prototype for collecting overdue installments through multilingual voice calls. Cashfree Relay orchestrates the workflow, Sarvam Indus handles the conversation, and Cashfree Payment Gateway hosts checkout.

## Demo flow

1. Relay receives a synthetic borrower and installment record. The profile supplies the starting language, overdue amount, and contact details.
2. Relay dispatches an outbound call using a committed Indus agent and a configured caller number.
3. If the borrower requests a link, Relay creates or retrieves the Cashfree sandbox link for that installment. A callback request or a claim of prior payment instead updates the collections queue.
4. A Cashfree event prompts a status lookup. Relay marks the installment paid only after Cashfree confirms payment.

## Build status

| Component | Evidence |
| --- | --- |
| Indus call | A direct Kannada phone test worked. Version 1 was committed and appeared in Indus's Instant Outbound picker. |
| Relay test canvas | The signed-in sandbox canvas was inspected using Playwright. |
| Outbound action | The isolated Relay HTTP action returned HTTP 200 and a Sarvam attempt ID with phone, name, amount, days past due, and starting language mapped from the webhook. The call action now sits only in the dedicated call branch. Pickup and audio for a Relay-triggered call remain unverified. |
| Payment link | The route and native Create Payment Link action were configured with webhook field mappings. The sandbox connection was selected and the isolated node test succeeded. |
| Payment status | The status lookup route and Fetch Payment Link Details action were configured with the webhook link ID. Cashfree checkout succeeded. A full Relay status run and a separate run with a sample payment event both fetched PAID and the full INR 1,200 from Cashfree. |

The [lender queue](docs/lender-queue-demo.md) persists verified payment totals, reported-payment holds, and requested callbacks locally. Open `/lender` in the trigger API to review the queue and refresh an installment from the Cashfree sandbox. The Relay agent is still a draft; automatic live webhook delivery and the Indus in-call tool remain pending.

[Relay setup runbook](docs/relay-setup.md) · [Webhook contract](docs/webhook-contract.md) · [Sample requests](examples/relay-events.json)

The demo uses synthetic records, a consenting test recipient, and Cashfree Test Environment. Keep credentials and webhook URLs in the platform secret stores.
