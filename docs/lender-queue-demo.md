# Lender queue: a 10-minute local demo

Open **[the lender screen](http://127.0.0.1:8000/lender)** after starting the server below. The manager's question is: *Who can I call next, and how much do they still owe?* The PowerShell path shows the same queue without screenshots, OCR, or a voice call.

## 1. Start a fresh queue (server PowerShell)

From the repository root, use a demo-only `TRIGGER_API_KEY` supplied privately to both shells. Keep keys out of command history, output and commits. Leave `CALL_API_URL` unconfigured. Typed previews need neither Sarvam nor Cashfree credentials.

```powershell
Set-Location .\calltrigger-api
python -m pip install -r requirements.txt
if (-not $env:TRIGGER_API_KEY) { throw 'Supply the local trigger key before starting.' }
$env:COLLECTIONS_DB = Join-Path $env:TEMP ("lender-demo-{0}.sqlite3" -f [guid]::NewGuid())
python -m uvicorn trigger_api:app --host 127.0.0.1 --port 8000
```

At `GET /lender`, enter the trigger key under **API key → Load queue**. API requests below send it as `X-API-Key`, never in a URL. `COLLECTIONS_DB` selects the SQLite file; the default is `calltrigger-api/collections.sqlite3`.

## 2. Register Meera and Ravi (client PowerShell)

In a second shell at the repository root, supply `DEMO_MEERA_PHONE` and `DEMO_RAVI_PHONE` from your **non-routable test fixtures**. Use two distinct 10-digit fixture values, never customer numbers or invented dialable numbers. If these fixtures aren't available, use the offline test in step 4.

```powershell
$ErrorActionPreference = 'Stop'
$base = 'http://127.0.0.1:8000'
if (-not $env:TRIGGER_API_KEY) { throw 'Supply the same local trigger key as the server.' }
if ($env:DEMO_MEERA_PHONE -notmatch '^[6-9][0-9]{9}$' -or
    $env:DEMO_RAVI_PHONE  -notmatch '^[6-9][0-9]{9}$' -or
    $env:DEMO_MEERA_PHONE -eq $env:DEMO_RAVI_PHONE) { throw 'Supply two distinct test fixture phones.' }
$headers = @{ 'X-API-Key' = $env:TRIGGER_API_KEY }
$ist = [DateTimeOffset]::UtcNow.ToOffset([TimeSpan]::FromMinutes(330))
$rows = @(
    @{ customer_id='demo-meera'; name='Meera'; phone_number=$env:DEMO_MEERA_PHONE; due_date=$ist.AddDays(-4).ToString('yyyy-MM-dd'); outstanding_amount=1200 }
    @{ customer_id='demo-ravi';  name='Ravi';  phone_number=$env:DEMO_RAVI_PHONE;  due_date=$ist.AddDays(-1).ToString('yyyy-MM-dd'); outstanding_amount=825.75 }
)
$id = @{}
foreach ($row in $rows) {
    $result = Invoke-RestMethod "$base/trigger/call?dry_run=true" -Method Post -Headers $headers -ContentType 'application/json' -Body ($row | ConvertTo-Json)
    if (-not $result.installment_id) { throw "Registration failed for $($row.name): $($result.status)" }
    $id[$row.name] = $result.installment_id
}
function Show-Queue {
    $q = Invoke-RestMethod "$base/queue" -Headers $headers
    foreach ($group in 'call_queue', 'other') {
        $q.$group | Select-Object @{n='list';e={$group}}, rank, name, paid_amount, outstanding_amount, status, reason, callback_at
    }
}
Show-Queue | Format-Table -AutoSize
```

**Check:** `GET /queue` returns eligible installments in `call_queue`, earliest due first, and all other installments in `other` with a reason. On a fresh database, from **08:00 inclusive to 19:00 exclusive IST**, Meera is first (INR 1,200), Ravi second (INR 825.75). Outside that window both rows still register; look in `other`. Preview never dials.

## 3. Show a claim and a callback without contacting anyone

Use `POST /queue/{installment_id}/already-paid` for Meera's claim and `POST /queue/{installment_id}/callback` for Ravi's requested time.

```powershell
Invoke-RestMethod "$base/queue/$($id.Meera)/already-paid" -Method Post -Headers $headers | Out-Null
$tomorrow = $ist.AddDays(1).ToString('yyyy-MM-dd')
$body = @{ callback_at = "${tomorrow}T10:00:00+05:30" } | ConvertTo-Json
Invoke-RestMethod "$base/queue/$($id.Ravi)/callback" -Method Post -Headers $headers -ContentType 'application/json' -Body $body | Out-Null
Show-Queue | Format-List
```

**Check:** Both rows are now in `other`. Meera's “already paid” claim pauses outreach; it does **not** credit money (`paid_amount=0`, `outstanding_amount=1200`). Ravi's callback is tomorrow at 10:00 IST. `callback_at` must be in the future, carry a UTC offset, and fall within `08:00 <= time < 19:00` in IST. Once due, he can rejoin the queue if still eligible; scheduling does not place a call. To check persistence, restart **only the uvicorn command** in the same server shell and repeat `Show-Queue`.

## 4. Verify a payment: fixture proof or Cashfree sandbox

**Offline proof:** With the requirements installed, run this from the repository root. The tests need no credentials or network:

```powershell
python -m pytest -q calltrigger-api/test_lender_queue.py calltrigger-api/test_cashfree_status.py
```

These tests use fixtures, not a Cashfree transaction. For an INR 1,200 installment, two refreshes reporting **INR 500 paid to date** leave **INR 700** outstanding both times. A later total of **INR 1,200** leaves zero, moves the paid row to `other`, and makes the next eligible borrower first. The tests use their own database, not the screen's data.

**Sandbox proof:** Use this path only if a matching test link already exists. Supply `CASHFREE_PG_CLIENT_ID` and `CASHFREE_PG_CLIENT_SECRET` to the **server process only**, before starting it. In step 2 use the sandbox installment's synthetic profile and exact due date instead of the rolling date. To see a fully paid Meera give way to Ravi, run the refresh before step 3's holds, during calling hours.

The queue uses the Relay call contract's installment ID, derived from customer ID (or phone if absent) and normalized due date. It looks up `emi-<installment_id>` using the ID returned in step 2. Link ID, owner phone, INR currency and **original** amount (INR 1,200 for Meera, even after a partial payment) must match. Another installment's confirmed link cannot verify this debt.

```powershell
1..2 | ForEach-Object {
    Invoke-RestMethod "$base/queue/$($id.Meera)/refresh" -Method Post -Headers $headers |
        Select-Object name, paid_amount, outstanding_amount, status
}
```

`POST /queue/{installment_id}/refresh` reads the existing sandbox link and applies its verified **cumulative** paid amount. The client sends no payment data. A repeat cannot credit the same payment twice; a failed or mismatched lookup leaves the last verified balance intact. This feature creates no payment link and receives no automatic live payment webhook.
