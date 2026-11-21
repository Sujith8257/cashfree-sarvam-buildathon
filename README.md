# Cashfree × Sarvam Buildathon

A sandbox prototype for collecting overdue installments through multilingual voice calls. Cashfree Relay orchestrates the workflow, Sarvam Indus handles the conversation, and Cashfree Payment Gateway hosts checkout.

**Start here:** [Two-minute judge demo](docs/judge-demo.md) · [Lender screen setup](docs/lender-queue-demo.md) · [Seven-day ranking benchmark](evaluation/README.md).

## Demo flow

1. Relay receives a synthetic borrower and installment record. The profile supplies the starting language, overdue amount, and contact details.
2. Relay dispatches an outbound call using a committed Indus agent and a configured caller number.
3. A separate Relay payment-request event creates or retrieves the sandbox link for that installment. In-call handoff needs a live rehearsal. The manager can record a callback, promise, hardship, or claim in the local queue.
4. A Cashfree event prompts a status lookup. The trigger API records payment only after a separate authenticated sandbox lookup confirms the installment and amount.

## Build status

| Component | Evidence |
| --- | --- |
| Indus call | A direct Kannada phone test worked. Version 1 was committed and appeared in Indus's Instant Outbound picker. |
| Relay test canvas | The signed-in sandbox canvas was inspected using Playwright. |
| Outbound action | The active sandbox copy accepted a live webhook, took the dedicated call branch, and returned HTTP 200 with an Indus attempt ID. The request used Indus v2 and the Kannada profile language. Pickup and audio for this run remain unverified. |
| Payment link | The route and native Create Payment Link action were configured with webhook field mappings. The sandbox connection was selected. The active sandbox webhook also created a fresh payment link from a separate payment request event. |
| Payment status | The status lookup route and Fetch Payment Link Details action were configured with the webhook link ID. Cashfree checkout succeeded. A full Relay status run and a separate run with a sample payment event both fetched PAID and the full INR 1,200 from Cashfree. |

The live Relay sandbox webhook expects an outer `data` object. The [lender queue](docs/lender-queue-demo.md) persists confirmed payments, claims, callbacks, promises and contact stops in SQLite. It can reconcile from the lender's **Refresh payment** action or a [signed Cashfree payment-link event](docs/webhook-contract.md#confirm-checkout). The new local receiver has been exercised with signed fixtures; a Cashfree-originated delivery to the deployed receiver and the Indus in-call tool still need a live end-to-end rehearsal.

[Relay setup runbook](docs/relay-setup.md) · [Webhook contract](docs/webhook-contract.md) · [Sample requests](examples/relay-events.json)

The demo uses synthetic records, a consenting test recipient, and Cashfree Test Environment. Keep credentials and webhook URLs in the platform secret stores.
