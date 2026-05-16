# FinBridge — Product Requirements Document

Companion to [ARCHITECTURE.md](./ARCHITECTURE.md) and [HLD.md](./HLD.md). This document specifies *what* must be true at submission, expressed as user-visible requirements with acceptance criteria.

---

## 1. Problem Statement

Mid-sized businesses exchange financial information with their accounting firms through scattered, informal channels (email, WhatsApp, shared drives). Accountants then re-key that data into systems like Zoho, QuickBooks, or Tally. The result: high manual labor, lost documents, slow month-end close, and brittle audit trails.

**FinBridge** is a three-tier multi-tenant SaaS that turns this informal exchange into a structured workflow:

1. Companies upload financial documents directly to the platform.
2. Claude's vision extracts each document into a structured transaction record.
3. Accountants review, refine, and approve the transactions.
4. Approved data and MIS reports flow back to the company.

This document defines the requirements that must be met within a 48-hour hackathon build.

---

## 2. Personas

### P1 — Platform Admin ("Anita")
- **Context:** Runs the FinBridge SaaS internally.
- **Goal:** Onboard new accounting firms onto the platform.
- **Pain:** Wants a fast, low-touch firm creation flow with sensible defaults.
- **In FinBridge:** Creates firms + their first firm admin in one step.

### P2 — Firm Admin ("Rohan")
- **Context:** Partner at a 25-person accounting firm. Owns operations.
- **Goal:** Onboard client companies and configure how their books are categorized.
- **Pain:** Each client has different payment heads (Manufacturing vs IT vs Services).
- **In FinBridge:** Creates companies, applies a payment-head template, manages accountants and company users.

### P3 — Accountant ("Priya")
- **Context:** Staff accountant; handles books for 8–12 client companies.
- **Goal:** Process inbound transactions quickly and accurately.
- **Pain:** Today she keys invoices from photos and scanned PDFs by hand.
- **In FinBridge:** Reviews AI-extracted transactions, corrects fields, assigns payment heads, approves; uploads MIS reports back to clients.

### P4 — Company User ("Vikram")
- **Context:** Accounts assistant at a manufacturing company. Receives bills from vendors.
- **Goal:** Get bills into the books without typing them.
- **Pain:** Today he photographs invoices and emails them to the accountant.
- **In FinBridge:** Drags an invoice photo or PDF into the platform; the AI fills in vendor, amount, line items; he tweaks if needed and submits.

---

## 3. Functional Requirements

Priority: **P0** = must work for demo · **P1** = nice-to-have, cut last · **P2** = aspirational, cut first.

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Login with email + password; receive a JWT scoped to role + tenant. | P0 |
| FR-2 | Platform admin can create accounting firms and an initial firm admin user. | P0 |
| FR-3 | Firm admin can create companies under their firm, with selectable business type (Manufacturing / IT / Services). | P0 |
| FR-4 | Creating a company auto-applies a 2-level payment-head template based on business type. | P0 |
| FR-5 | Firm admin can add / view payment heads and sub-heads for any company in their firm. | P0 |
| FR-6 | Firm admin can add accountants to their firm and additional users to a company. | P0 |
| FR-7 | Company user can upload an invoice file (image or PDF, ≤ 10 MB). | P0 |
| FR-8 | On upload, the system extracts the invoice into a structured transaction using Claude vision (or fixture/gemini fallback). | P0 |
| FR-9 | Company user sees the extracted fields immediately, can edit any field, and submits for review. | P0 |
| FR-10 | Company user can record a non-invoice transaction (payment or salary register) manually. | P0 |
| FR-11 | Accountant sees a queue of `pending_review` transactions for all companies in their firm. | P0 |
| FR-12 | Accountant opens a transaction and sees the original file alongside the editable fields. | P0 |
| FR-13 | Accountant can edit any field (including payment head assignment) and approve or reject (with reason). | P0 |
| FR-14 | Accountant can upload an MIS report (PDF or other file) tied to a company. | P0 |
| FR-15 | Company user can list and download MIS reports for their company. | P0 |
| FR-16 | All key actions (upload, submit, approve, reject, report upload) are recorded in an audit log. | P0 (writes) / P2 (UI) |
| FR-17 | Dashboard shows counts, recent transactions, top expense heads — scoped to caller's role and tenant. | P1 |
| FR-18 | Every API request is authenticated; cross-tenant access returns 403. | P0 |
| FR-19 | Seed script populates a demo-ready dataset (firms, companies, users, payment heads, bills, extractions, transactions, one report). | P0 |
| FR-20 | One-command Docker deployment that runs locally. | P0 |
| FR-21 | Invoice extraction includes Indian GST fields: vendor GSTIN, customer GSTIN, place of supply, HSN/SAC per line item, CGST/SGST/IGST splits, reverse-charge flag. | P0 |
| FR-22 | Accountant can return a transaction to the company user with a "needs more info" note (state `needs_info`) instead of approving or rejecting; company user can edit and resubmit. | P1 |
| FR-23 | On submit, the system detects potential duplicates by `(company_id, vendor, invoice_no)` against accepted transactions and surfaces a warning to the accountant. | P1 |

---

## 4. Acceptance Criteria

Each FR is satisfied when the criterion below is observable in a clean Docker run, using only the seeded credentials.

| FR | Acceptance Criterion |
|---|---|
| FR-1 | Posting valid credentials returns a JWT with claims `sub`, `role`, `firm_id`, `company_id`, `exp`. Invalid credentials return 401. |
| FR-2 | Logged in as platform admin, posting `{name, admin_email, admin_password}` creates a firm and firm_admin user; both appear in subsequent GETs. |
| FR-3 | Logged in as firm admin, posting `{name, business_type, admin_email, admin_password}` creates a company scoped to my firm; another firm's admin cannot see it. |
| FR-4 | Immediately after company creation, `GET /companies/{id}/payment-heads` returns a 2-level tree matching the template for `business_type`. |
| FR-5 | Posting `{name, parent_head_id?}` to `/companies/{id}/payment-heads` adds it; duplicates within (company, parent, name) are rejected with 409. |
| FR-6 | Firm admin can post `{role: accountant, email, password}` and `{role: company_user, email, password, company_id}`; these users can subsequently log in. |
| FR-7 | Posting a multipart file with non-image/non-PDF MIME returns 400; file > 10 MB returns 413; valid file returns 200 with a transaction id. |
| FR-8 | For a seeded demo bill, the response includes `extracted.vendor`, `extracted.total`, `extracted.invoice_date`, and `extracted.line_items` non-empty. |
| FR-9 | The UI renders the extraction in an editable form within ≤ 2s of upload completion (extraction itself may take up to 15s — see NFR-2); submitting transitions status to `pending_review`. |
| FR-10 | Posting to `/transactions/manual` with type `payment` or `salary_register` creates a transaction with `status=pending_review` (no AI involved). |
| FR-11 | Logged in as accountant, `GET /transactions?status=pending_review` returns every pending transaction across every company in my firm and none from other firms. |
| FR-12 | The transaction detail page renders the original attachment via `/transactions/{id}/attachment` next to the editable form. |
| FR-13 | Posting `/transactions/{id}/approve` transitions to `accepted` only from `pending_review`; otherwise 409. Reject requires a non-empty `reason`. |
| FR-14 | Posting a multipart file + `title` + `company_id` creates a report row; non-accountants get 403. |
| FR-15 | `GET /reports?company_id=…` lists reports; `GET /reports/{id}/file` streams the file with the original filename. |
| FR-16 | Inserting / mutating a transaction inserts an `audit_log` row with `actor_user_id`, `action`, `entity_type=transaction`, `entity_id`, and timestamp. |
| FR-17 | `GET /dashboard/summary` returns counts by status, top 5 expense heads by amount, and last 10 transactions — scoped to the caller. |
| FR-18 | A user from Firm A receives 403 when GETing transactions belonging to Firm B's companies (verified by one smoke test). |
| FR-19 | After `make fresh`, login works for all seeded roles; the accountant queue shows pre-staged pending transactions; the company dashboard shows accepted ones; one MIS report is present. |
| FR-20 | `cp .env.example .env && docker compose up --build` results in a reachable `http://localhost:8000` with the SPA served. |
| FR-21 | For a seeded Indian invoice, the extraction response includes non-null `vendor_gstin`, line-item `hsn_sac`, and either a CGST/SGST pair or `igst` whose sum equals `tax_amount` within ±1. |
| FR-22 | Posting `/transactions/{id}/request-info` with `{reason}` transitions status from `pending_review` to `needs_info`; the transaction returns to the company user's queue with the note visible and editable; on resubmit it returns to `pending_review`. |
| FR-23 | On transition to `pending_review`, if `(company_id, vendor, invoice_no)` matches an existing `accepted` transaction, the response includes `possible_duplicate_of=<id>` and the review queue renders a "possible duplicate" badge with a link to the original. |

---

## 5. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | One-command local deployment | `docker compose up --build` only |
| NFR-2 | End-to-end extraction latency (upload → preview rendered) | ≤ 15 s with live Claude, ≤ 2 s with fixture provider |
| NFR-3 | Browsers supported | Latest Chromium, Firefox, Safari (current minus one) |
| NFR-4 | Demo dataset reset time | `make fresh` in ≤ 60 s |
| NFR-5 | Concurrent users handled | 3 simultaneous logins (demo + judges) without observable degradation |
| NFR-6 | Auth | Bcrypt password hashes; JWT HS256 with env-supplied secret |
| NFR-7 | Tenant isolation | Service-layer enforcement; one smoke test proves cross-tenant 403 |
| NFR-8 | Logs | Backend writes structured logs to stdout (captured by docker logs) |
| NFR-9 | Accessibility | Keyboard navigation works on Login, Upload, Review pages; semantic HTML; no axe critical errors |
| NFR-10 | Documentation | README + ARCHITECTURE.md + HLD.md + PRD.md + PLAN.md + LLD.md present and consistent at submission |

---

## 6. Success Metrics (mapped to judging rubric)

| Judging criterion | Weight | What success looks like for FinBridge |
|---|---|---|
| Working demo | 30% | All 20 functional requirements verifiable in a single demo recording on a fresh `docker compose up`. |
| AI capability | 25% | Claude vision extraction surfaces vendor, totals, line items, dates with visible confidence cues; works on at least 5 distinct seeded bills including 2 messy phone photos. |
| Architecture & code quality | 20% | Clean module separation (api / services / db / extraction); explicit provider abstraction; ADRs documented; tenant scoping in one place; no dead code in submission. |
| UX & polish | 15% | shadcn-styled UI; consistent layout shell; loading + empty states everywhere; toast notifications for state changes; side-by-side review screen. |
| Creativity / stretch | 10% | Multi-provider extraction abstraction; payment-head templates by business type; confidence scoring per field; audit log; dashboard with top-expense chart. |

---

## 7. In Scope vs Out of Scope

### In scope (this build)
- Everything listed under §3 with priority P0 or P1.
- Local Docker deployment.
- Documentation set (this folder).
- 5–8 slide presentation deck.
- 2–3 minute demo video.

### Out of scope (intentionally deferred; mention in roadmap slide)
- Integration with Zoho / QuickBooks / Tally.
- Payment gateway integration.
- Advanced reporting engine (anything beyond file upload/download).
- Mobile app or PWA.
- Bulk bank statement upload with auto-categorization.
- Notification systems (email / in-app).
- Postgres row-level security.
- Refresh tokens, password reset, MFA, email verification.
- Soft deletes, record versioning beyond audit log.

---

## 8. Constraints

- **Time:** 48 hours, one developer + Claude Code.
- **Budget:** $0 — no paid API keys available. AI extraction defaults to fixture provider; Claude/Gemini opt-in via env var.
- **Stack:** Python + React + PostgreSQL (locked by user).
- **Deployment:** Local only, via docker-compose.
- **Submission artifacts:** GitHub repo + README + presentation + (optional but recommended) demo video.

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AI extraction quality on real-world phone photos | M | H | Curate clean demo set; surface per-field confidence; allow user edits before submit |
| No Anthropic API key for live demo | Confirmed | M | Fixture provider as default; documented in README and demo deck |
| PDF handling (native vs scanned) inconsistencies | M | M | Hour-1 smoke test against representative samples before any code |
| Tenant isolation bug leaks data across firms | L | H | Single `tenant_scope()` dependency; one smoke test |
| Time blown on admin CRUD UIs that don't move the needle | M | M | Seed most admin data; one create flow per tier suffices |
| Docker production build issues at hour 22 | M | H | Get FastAPI-serves-static-React working end of Day 1, not Day 2 |
| Frontend scope creep | H | M | Tiered page priority; Tier 1 (login, upload, review) shipped first |

---

## 10. Open Questions

- Is there a hackathon-supplied API credit grant for Claude? (Action: ask organizers.)
- Will judges install Claude Code locally to test live extraction, or are screenshots/video sufficient? (Default assumption: video.)
- Are seeded demo passwords acceptable in the public README, or should they be regenerated per build? (Default: documented seeded passwords in README; explicit note that this is hackathon-only.)

---

## 11. References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system structure & ADRs
- [HLD.md](./HLD.md) — flows, schema, API surface
- [PLAN.md](./PLAN.md) — implementation schedule
- [LLD.md](./LLD.md) — module-level design
- `FinBridge_Hackathon_Problem_Statement.pdf` — original problem statement
