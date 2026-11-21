# Read a borrower’s own words

In the local API's **`/docs`**, authorize with `TRIGGER_API_KEY` and open `POST /queue/{iid}/review-note`. Use a registered installment ID from `GET /queue`. Submit one synthetic `note`, or one short `audio` WAV. The server needs a Sarvam subscription key; the review never calls a phone number or updates an installment.

Try `Salary 5th ko aayegi. Maine branch mein de diya.` The manager can see separate candidate signals for salary timing and a **claim** of prior payment, each with a quote copied from the source. A salary date is not a promise to pay. A branch-payment claim is not proof that the account has settled. Use the existing claim or payment refresh action separately after reviewing the evidence.

Audio is limited to mono, 16-bit PCM WAV at 8 or 16 kHz, shorter than 30 seconds and at most 1 MiB. [Saaras](https://docs.sarvam.ai/api-reference/speech-to-text/transcribe) produces the code-mixed transcript; [Sarvam-105B](https://docs.sarvam.ai/api/token-factory/chat-completions) labels excerpts. Phrase timestamps are included only when they can be matched to one source phrase. Unknown labels, duplicate evidence and quotes absent from the transcript are discarded. Labels are suggestions, not inferred payment facts or ranking features. Audio and text are sent to Sarvam; the app does not save them.
