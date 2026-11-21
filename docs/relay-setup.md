# Relay setup runbook

## Connect the sandbox services

1. Open the Cashfree Merchant Dashboard, switch to **Test Environment**, and open **Payment Gateway → Relay**.
2. Add a **Cashfree Payments** connection with the Payment Gateway test Client ID and Client Secret. Select it on both payment-link actions.
3. In Indus, configure a caller number and confirm it is active. Commit the voice agent version. Use **Deploy with code → Instant outbound** to confirm it is selectable and to locate the telephony connection ID.
4. Put the Indus Voice Agents API key in a Relay secret property. Keep the key in the `X-API-Key` request header. A Cashfree connection and a Sarvam Voice connection authenticate different services. [Relay connections](https://www.cashfree.com/docs/tools-ai/relay/add-connections) · [Indus outbound API](https://docs.sarvam.ai/voice-agents/api/instant-outbound/create)

## Configure the actions

Use **Inbound Webhook** as the trigger. Seed **Update initial Data** with a sample wrapped in `data` for the canvas data selector. The HTTP payload sent to the generated URL and the shape exposed by Relay should be confirmed with the test trigger before activation. [Relay agent setup](https://www.cashfree.com/docs/tools-ai/relay/create-agent)

| Route | Action | Mapping |
| --- | --- | --- |
| `start_collection_call` | HTTP POST to Sarvam Instant Outbound | Use the committed agent version, telephony connection, caller number, and the validated profile phone and language. Map name, amount, and days past due to the agent variables. |
| `create_payment_link` | Cashfree Payments → Create Payment Link | Map the verified amount, name, phone, and stable installment link ID. Use INR and a short purpose. |
| `fetch_payment_status` | Cashfree Payments → Fetch Payment Link Details | Map the stored link ID and use the returned status to reconcile the installment. |
| `PAYMENT_LINK_EVENT` | Cashfree Payments -> Fetch Payment Link Details | Read the nested event link ID. Fetch Cashfree state before treating it as paid. |
| Unrecognized event | End the flow | Record the unsupported event for troubleshooting. |

Place the outbound call **inside its own route** before running the complete agent. Relay rejoins branches at their downstream continuation, so an HTTP call placed after the join can run for payment events.

The Instant Outbound endpoint is `POST https://apps.sarvam.ai/api/outbounds/v1/orgs/{org_id}/workspaces/{workspace_id}/outbounds`. The following body uses placeholders and demonstrates the language override. Bind each placeholder through Relay's data selector or secret/property controls as appropriate. Supply a supported language name such as Kannada, Telugu, or Hindi for `initial_language_name`. [Sarvam request schema](https://docs.sarvam.ai/voice-agents/api/instant-outbound/create)

```json
{
  "app_config": {
    "app_id": "<INDUS_AGENT_ID>",
    "app_version": 1,
    "app_type": "agent",
    "connection_config": {
      "connection_id": "<TELEPHONY_CONNECTION_ID>",
      "agent_phone_number": "<TEST_CALLER_E164>"
    },
    "app_overrides": {
      "initial_language_name": "Kannada"
    },
    "agent_variables": {
      "userName": "<SYNTHETIC_BORROWER_NAME>",
      "outstandingAmount": "1200"
    }
  },
  "user_config": {
    "user_phone_number": "<VERIFIED_TEST_RECIPIENT_E164>"
  }
}
```

Sarvam returns an `attempt_id` when it accepts the request. Confirm the call connected and used the intended language in the call logs. Add another supported borrower language, such as Tamil, and run the same check. [Sarvam call results](https://docs.sarvam.ai/voice-agents/api/instant-outbound/webhook-payload)

## Verify the demo

1. Run **Test Step** on the isolated payment node after selecting the sandbox connection. Confirm that Cashfree returns a link for the expected amount and installment.
2. Complete checkout in the sandbox. Fetch the link and verify the amount, currency, and `PAID` status before updating the queue.
3. Run the phone workflow with two test profiles in distinct languages. Ask for a link on one call and request a callback on the other.
4. Replay a link request and payment event. Check that the same installment link is reused and that payment state is applied once.

[Create Payment Link](https://www.cashfree.com/docs/api-reference/payments/latest/payment-links/create-payment-link) · [Fetch Payment Link Details](https://www.cashfree.com/docs/api-reference/payments/latest/payment-links/fetch-payment-link-details) · [Payment Link Webhooks](https://www.cashfree.com/docs/api-reference/payments/latest/payment-links/webhooks)
