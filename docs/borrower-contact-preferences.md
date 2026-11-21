# Stop automated borrower outreach

1. Open `/docs` → **Authorize** with `X-API-Key`. Use `GET /queue` to find a known installment by its customer reference and due date, and copy its `installment_id`.
2. Send `POST /queue/{iid}/contact-preference` with `{"reason":"no_contact"}` or `{"reason":"hardship"}`, according to what the borrower reported. Both stop automated outreach to that registered phone number. Neither action calls the borrower, sends a message, or changes a payment balance.
3. Read the refreshed queue with `GET /queue`. Affected installments move out of `call_queue`. Their reasons explain the stop in English and include a Kannada support message. For hardship, offer human support only if the borrower asks. For a no-contact request, do not initiate contact. No automatic human callback is scheduled.

The response includes the effective `contact_preference`, the installment `status`, and a readable `reason`. The endpoint does not accept a name or phone override. An unknown installment returns `404`.

**Scope:** One lender per `COLLECTIONS_DB`. The key is the validated, normalized Indian mobile number already registered on the installment; a name, customer ID, or new phone supplied by the request is not used. All existing and later installments at the same number share the stop, including when the number is shared. Different numbers are not linked. Keep the same SQLite file across restarts. Rescans, repeated reports and callbacks cannot restart outreach. A no-contact request takes precedence over a later hardship report; there is no automatic expiry or resume action.

Fully verified payments still show `paid`; an unverified paid-in-full claim still shows `payment_hold`. Their reasons also display the contact stop. Typed and notebook previews and live dispatch use this rule, and live requests recheck the stop immediately before handoff. The trigger API cannot recall a dispatch already in flight or stop a provider contacted independently. The recording endpoint does not send support text to the borrower.
