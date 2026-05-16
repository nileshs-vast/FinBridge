# FinBridge — Demo Video Script

Target runtime: ~3 minutes. Record in one take after `make fresh`. Browser tabs pre-loaded for each role at `http://localhost`.

---

## [0:00 – 0:15] Setup

**Show:** Terminal window.

```bash
make fresh
```

Wait for the output to complete:

```
✓ Seed complete
  Firm:    Sharma & Co.
  Companies: Acme Manufacturing, Lumen IT
  Users (password: Finbridge#2026):
    platform@finbridge.local  — platform_admin
    admin@sharmaco.local      — firm_admin
    priya@sharmaco.local      — accountant
    ...
  Transactions: 4 accepted, 4 pending_review, 2 draft_ai
```

**Say:** "One command — `make fresh` — wipes the database, rebuilds, and loads 10 pre-staged transactions and 6 demo users. No manual setup."

Switch to the browser. The address bar reads `http://localhost`. The FinBridge login screen is visible.

---

## [0:15 – 0:45] Company User Flow

**Login:** `upload@acme.local` / `Finbridge#2026`

**Say:** "We're logging in as a company user at Acme Manufacturing. Their job is to upload documents."

After login, the dashboard or upload page is visible. Click **Upload Document** in the navigation.

**Show:** The upload interface — drag-and-drop area or file picker.

Upload the file `tata_steel_invoice.pdf` from the `sample_invoices/` folder (the fixture provider matches by filename stem and returns the pre-built Tata Steel extraction).

**Say:** "Acme has received a ₹4.95 lakh invoice from Tata Steel. We upload it — PDF, image, Excel, any format works."

The upload completes. The extraction preview loads within 2–3 seconds.

**Show:** The extraction preview screen with fields populated:
- Vendor: Tata Steel Ltd
- GSTIN: 27AAACT2727Q1ZW
- Invoice No: TATA/2024/001
- Date: 2024-04-05
- Subtotal: ₹4,20,000
- CGST: ₹37,800 | SGST: ₹37,800
- Total: ₹4,95,600
- Line items expanded

**Say:** "The AI has extracted every field — vendor name, GSTIN, invoice number, date, GST breakdown — in under 3 seconds. The company user can review, make any corrections, assign a payment head, and submit."

Select the payment head "Raw Materials → Steel" from the dropdown. Click **Submit for Review**.

**Say:** "Submitted. It's now in the accountant's review queue."

---

## [0:45 – 1:30] Accountant Review Flow

Log out. Log in as: `priya@sharmaco.local` / `Finbridge#2026`

**Say:** "Now we're Priya, the accountant at Sharma & Co. She reviews transactions for all her client companies from a single queue."

**Show:** The review queue. The Tata Steel transaction appears at the top with status `pending_review`. There are also other pre-seeded transactions visible: Mahindra Logistics, L&T, Bajaj Electricals, SAIL.

**Say:** "Four pending transactions, one just submitted. Let's open the Tata Steel invoice."

Click the Tata Steel transaction row.

**Show:** The transaction detail page — the original PDF rendered on the left, extracted fields on the right.

**Say:** "Side by side: the original document and the extracted data. Notice the confidence badges next to each field — the AI tells Priya exactly how certain it was about each value."

**Show:** The confidence badges (e.g., "Vendor 97%", "Total 95%") in green next to field labels. Point out a field with a yellow or red badge if one is visible.

**Say:** "Green means the AI is confident. Yellow or red means Priya should double-check — maybe the document was a photo taken at an angle."

If the payment head is not already set, select "Raw Materials → Steel" from the payment head dropdown.

Click **Approve**.

**Show:** The status updates to `accepted`. A toast notification confirms the action. The transaction disappears from the pending queue.

**Say:** "Approved. Now scroll down to the audit trail."

**Show:** The audit trail panel at the bottom-left of the page — a chronological list showing "Uploaded", "Submitted for review", "Approved" with timestamps.

**Say:** "Full audit trail: every status change, who made it, and when — automatically. No extra effort from Priya."

---

## [1:30 – 2:00] Dashboard and Reports

Log out. Log in as: `admin@sharmaco.local` / `Finbridge#2026`

**Say:** "As the firm admin at Sharma & Co., we get a firm-wide view."

**Show:** The dashboard page. Point out:
- Summary cards: total transactions, accepted this month, pending review, total amount processed
- Recent activity table showing the latest transactions across both companies
- Top payment heads chart (bar chart showing spending by category)

**Say:** "At a glance: how many transactions are flowing, what's been approved, and where the money is going — across all companies in the firm."

Click **Reports** in the navigation.

**Show:** The reports page for Acme Manufacturing — the April 2024 MIS report is listed.

**Say:** "Accountants upload MIS reports here. Company users download them. The same platform handles the data going in and the analysis coming back out."

---

## [2:00 – 2:30] Multi-Tenant Isolation

Stay logged in as `admin@sharmaco.local`. Navigate to **Companies**.

**Show:** Two companies listed: Acme Manufacturing and Lumen IT.

**Say:** "The platform supports multiple companies under the same firm. Acme's transactions are invisible to Lumen IT's users, and vice versa. It's enforced in every API request — not just in the UI."

Click into Lumen IT's company view.

**Show:** Lumen IT has its own payment heads, its own transaction history, its own reports — none of Acme's data is visible.

**Say:** "Three-tier tenancy: Platform, Firm, Company. Each layer can only see what it owns. A cross-tenant isolation test in our smoke suite verifies this on every build."

---

## [2:30 – 3:00] Architecture Callout + Close

Switch back to the terminal window.

**Show:** The `docker-compose.yml` (briefly) or just the terminal output from `make up`.

**Say:** "Everything you just saw runs in three Docker containers: nginx on port 80 proxying requests to FastAPI, which serves the React frontend and all API routes. Postgres stores everything. One `docker compose up --build`, no configuration required."

**Show:** The browser at `http://localhost`. The login screen is clean and responsive.

**Say:** "Upload to approval in under 60 seconds. Accountants stop doing data entry and start doing accounting. That's FinBridge."

---

## Recording Checklist

- [ ] `make fresh` completed successfully before starting recording
- [ ] Browser font size at 125% for legibility
- [ ] All three role tabs pre-opened and pre-positioned
- [ ] Terminal font size at 16pt minimum
- [ ] Audio: microphone levels checked, room quiet
- [ ] Screen resolution: 1920×1080 or 1440×900
- [ ] Upload file ready: `sample_invoices/tata_steel_invoice.pdf`
- [ ] Fallback: fixture extraction is offline — demo works without internet

## Timing Notes

| Segment | Target | Actual |
|---|---|---|
| Setup (`make fresh`) | 0:00 – 0:15 | |
| Company user upload + extract + submit | 0:15 – 0:45 | |
| Accountant queue + review + approve | 0:45 – 1:30 | |
| Dashboard + reports | 1:30 – 2:00 | |
| Multi-tenant isolation | 2:00 – 2:30 | |
| Architecture callout + close | 2:30 – 3:00 | |
