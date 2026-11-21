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
| Outbound action | The HTTP action maps the webhook phone, name, amount, days past due, and starting language to Sarvam Instant Outbound. The start-call route is configured. Moving the HTTP action into that branch and testing the Relay-triggered call are pending. |
| Payment link | The route and native Create Payment Link action were configured with webhook field mappings. The isolated node test stopped at authentication because no Cashfree Payments connection was selected. |
| Payment status | The status lookup route and Fetch Payment Link Details action were configured with the webhook link ID. The Cashfree connection and an end-to-end checkout verification are pending. |

[Relay setup runbook](docs/relay-setup.md) · [Webhook contract](docs/webhook-contract.md) · [Sample requests](examples/relay-events.json)

The demo uses synthetic records, a consenting test recipient, and Cashfree Test Environment. Keep credentials and webhook URLs in the platform secret stores.
