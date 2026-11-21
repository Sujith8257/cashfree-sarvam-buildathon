# Cashfree × Sarvam Buildathon

A sandbox prototype for collecting overdue installments through multilingual voice calls. Cashfree Relay orchestrates the workflow, Sarvam Indus handles the conversation, and Cashfree Payment Gateway hosts checkout.

**Start here:** [Two-minute judge demo](docs/judge-demo.md) · [Lender queue setup](docs/lender-queue-demo.md) · [Seven-day ranking benchmark](evaluation/README.md).

## Demo flow

1. Relay receives a synthetic borrower and installment record. The profile supplies the starting language, overdue amount, and contact details.
2. Relay dispatches an outbound call using a committed Indus agent and a configured caller number.
3. Submit a `create_payment_link` event with the test recipient's email. Relay creates the sandbox checkout and requests Cashfree's email notification. The manager can record a callback, promise, hardship, or claim in the local queue.
4. Complete the sandbox checkout and call `POST /queue/{iid}/refresh` (in `/docs`) to verify it. The trigger API records payment only after an authenticated sandbox lookup confirms the installment and amount.

## Build status

| Component | Evidence |
| --- | --- |
| Indus call | A live Relay webhook launched a connected Indus v4 call. A separate Kannada test verified profile-based language selection. |
| Payment link and email | A direct `create_payment_link` webhook produced an active sandbox checkout with email enabled. The test recipient confirmed receipt. Cashfree sends payment-link SMS in production only. |
| Payment status | A prior sandbox checkout completed and the Relay status route fetched `PAID`. A sample payment event also ran through the lookup branch. |
| Supabase | The local watcher saves generated payment links and completed Relay calls to private Storage. The v4 call's transcript, summary, and WAV were read back successfully. |

The demo uses the inbound webhook for Relay sandbox agent `43703` and expects an outer `data` object. The direct payment-link event is the verified demo path. The Indus in-call tool still needs to send the expected request body to this endpoint.

The [lender queue](docs/lender-queue-demo.md) persists confirmed payments, claims, callbacks, promises, and contact stops in SQLite. It can reconcile from `POST /queue/{iid}/refresh` or a [signed Cashfree payment-link event](docs/webhook-contract.md#confirm-checkout). The local receiver has been exercised with signed fixtures. A Cashfree-originated event to the deployed receiver still needs a live check.

[Relay setup runbook](docs/relay-setup.md) · [Webhook contract](docs/webhook-contract.md) · [Sample requests](examples/relay-events.json)

The demo uses synthetic records, a consenting test recipient, and Cashfree Test Environment. Keep credentials and webhook URLs in the platform secret stores.
