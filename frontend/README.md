# Cashfree - Loan Recovery & Agent Interactions CRM

A modern, clean, and responsive UI built with **React**, **Vite**, **TypeScript**, and **Tailwind CSS / Shadcn UI** designed specifically for the Supabase `customers` and `agent` database schema.

---

## 🚀 Features

1. **Dashboard & Portfolio Metrics**
   - Total Portfolio Outstanding vs Disbursed Principal
   - Repayment progress bar and percentage
   - Total Promised to Pay (PTP) commitments pipeline
   - Agent Call Success and Conversion rate
   - Active borrower accounts and average interest rate

2. **Borrowers & Loans View (`customers` table)**
   - Display `customer_id`, `name`, `phone_number`, `email`, `language`, `lending_date`, `due_date`, `principal_amount`, `interest_rate`, `outstanding_amount`
   - Real-time search by borrower name, phone, email, or customer ID
   - Filter by borrower language
   - Sort by Outstanding Amount, Due Date, Principal, or Name
   - Toggle between dense Table view and Responsive Grid Card view
   - Add new customer dialog with immediate persistence

3. **Agent Calls & Log View (`agent` table)**
   - Display `interaction_id`, `customer_id`, `call_datetime`, `call_status`, `language_used`, `call_summary`, `customer_feedback`, `payment_status`, `promise_to_pay_date`, `promise_to_pay_amount`, `call_recording`, and `call_transcript`
   - Filter by call outcome (`Completed`, `Busy`, `No Answer`, `Failed`)
   - Filter by payment status (`Promised to Pay`, `Paid`, `Pending Review`, `Disputed`, `Refused`)
   - Conversational Transcript Viewer with speaker separation (`[Agent]` vs `[Customer]`), in-transcript keyword search, and copy-to-clipboard
   - Integrated Audio Player with waveform scrubber, speed selector (1x, 1.25x, 1.5x, 2x), and mute/reset controls
   - Log new call interaction dialog linked to any borrower

4. **Supabase Integration & Zero-Config Demo Mode**
   - Directly connects to Supabase when credentials are provided in `.env` or via the in-app **"Supabase Live"** setup modal.
   - Zero-friction demo fallback with realistic multi-language loan data and transcripts when credentials are not yet entered.
   - Built-in SQL schema viewer and copy button to run in Supabase SQL Editor.

---

## 🛠️ Quick Start

### 1. Install dependencies
```bash
npm install
```

### 2. Run the development server
```bash
npm run dev
```

Open your browser at `http://localhost:5173`.

### 3. Build for production
```bash
npm run build
```

---

## Login, signup, and Supabase setup

1. Open Supabase SQL Editor and run the complete script in [supabase/setup.sql](supabase/setup.sql). The same script is available under **Supabase connection & SQL setup → SQL Table Schemas** on the login page.
2. Enable the Email provider in Supabase Authentication. Configure your Site URL and allowed Redirect URLs for your deployed origin and local development URL.
3. Set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` in `.env`, then restart Vite or rebuild for deployment. Existing installations can also use `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. A connection saved through the setup dialog takes precedence on that browser.
4. Open #/signup to create an account. If email confirmation is enabled, confirm your email before signing in at #/login.

Call queue (local demo only):
1. In `calltrigger-api`, start the collections API: `python -m uvicorn trigger_api:app --host 127.0.0.1 --port 8000`.
2. Give Vite the same `TRIGGER_API_KEY` (and `COLLECTIONS_API_URL` if the API runs elsewhere) in `frontend/.env` or the shell, then `npm run dev`.
3. The overview shows the call queue, and borrowers added or imported with a due date and open balance join it. The Vite dev/preview proxy forwards only `GET /api/queue` and `POST /api/trigger/call`, always with `dry_run=true`, so the dashboard never starts a call; the key stays on the Vite server.

Supabase Auth stores and verifies passwords. The SQL creates a profile automatically and applies row level security so each account can access its own borrowers and interactions. Existing records with a NULL user_id remain hidden until assigned explicitly to their owner's auth.users.id. Amounts are displayed as INR (₹) with Indian digit grouping; existing numeric values are not converted from another currency.

Live authentication requires a configured Supabase project. The dashboard requires an authenticated session; failed live writes return an error instead of saving locally.

