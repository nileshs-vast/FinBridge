# FinBridge — Presentation Deck
## 48-hour Hackathon | Speaker Notes

---

## Slide 1 — The Invoice Pile Problem

**Title:** The Invoice Pile Problem

Indian SMEs receive hundreds of vendor bills every month — steel suppliers, logistics partners, utility providers, contractors. Every one of those bills lands in an accountant's inbox as a PDF, a photo, or a printout. The accountant then manually keys in the vendor name, invoice number, date, total amount, GST breakdown (CGST, SGST, IGST), and the internal payment head for the ledger.

**The cost of manual entry:**
- 8–12 minutes per invoice, multiplied by hundreds of bills per month
- Error rate of 3–5% on manual keying — errors that surface only at month-end reconciliation
- No audit trail: who entered what, when, and whether it was verified
- Accountants spending most of their time on data entry rather than advisory work

**What breaks when this fails:**
- GST filings with wrong input-tax-credit amounts
- Payments made to the wrong vendor account
- Salary disbursements booked under the wrong cost centre
- MIS reports delivered late because the underlying data isn't clean

The problem is not unique — it affects every SME that works with an external accounting firm. FinBridge is the fix.

---

## Slide 2 — Solution: FinBridge

**Title:** FinBridge — From Pile to Ledger in Seconds

FinBridge gives accounting firms a structured SaaS workspace shared with their client companies. The workflow is three steps:

1. **Upload** — A company user uploads any document: vendor invoice (PDF or image), salary register (Excel), bank statement. Any format, any Indian vendor.

2. **Extract** — The AI layer (Claude vision or Gemini) reads the document and extracts structured fields: vendor name, GSTIN, invoice number, date, subtotal, CGST, SGST, IGST, line items, and a suggested payment head. This takes 2–5 seconds. The raw AI response is stored so nothing is lost.

3. **Review & Approve** — The accountant opens the transaction from a shared review queue. They see the original document on the left, extracted fields on the right. They correct any errors, assign the payment head, and click Approve. The transaction enters the accepted ledger with a full audit trail: who uploaded, when, who reviewed, when, what changed.

**Key properties:**
- Multi-company: one accountant can review transactions for all their client companies from a single queue
- Offline-capable: the fixture extraction provider works without any API key, making demos reliable
- Auditable: every status change and field edit is logged with a timestamp and user ID

---

## Slide 3 — Demo Flow

**Title:** Upload to Approval in Under 60 Seconds

```
Company User              AI Layer                  Accountant
     │                       │                          │
     ├── Upload bill ────────▶│                          │
     │   (PDF / image /       │                          │
     │    Excel)              │                          │
     │                       ├── Extract fields ─────────▶│
     │                       │   vendor name             │
     │                       │   invoice number          │
     │                       │   date, amount            │
     │                       │   CGST / SGST / IGST      │
     │                       │   line items              │
     │                       │   suggested payment head  │
     │                       │                          │
     │◀── Draft preview ─────┤                          │
     │    (editable)          │                          │
     │                       │                          │
     ├── Submit for review ──────────────────────────────▶│
     │                       │                          │
     │                       │                     ├── Review queue
     │                       │                     ├── Open transaction
     │                       │                     │   (document + fields
     │                       │                     │    side by side)
     │                       │                     ├── Edit if needed
     │                       │                     │
     │                       │                     ├── Approve ──▶ Accepted ledger
     │                       │                     │              + audit log entry
     │                       │                     └── Reject  ──▶ Status: rejected
     │                       │                                     + rejection note
     │◀── Status update ─────┼──────────────────────────┘
```

The fixture provider matches uploaded filenames to pre-built Indian invoice JSON files, making the demo fully reproducible offline. Switching to live Claude or Gemini extraction requires one environment variable change.

---

## Slide 4 — Architecture

**Title:** One Container, Three Tiers, Three AI Providers

**Tenancy model:**

```
Platform Admin
    └── Accounting Firm (e.g. Sharma & Co.)
            ├── Accountants (review all companies in firm)
            ├── Company A: Acme Manufacturing
            │       └── Company Users (upload only)
            └── Company B: Lumen IT
                    └── Company Users (upload only)
```

Every database row is scoped by `firm_id` and `company_id`. JWTs carry both claims. A single `tenant_scope()` FastAPI dependency enforces isolation — no Postgres RLS, isolation enforced in application code, verified by a cross-tenant smoke test.

**Deployment:**

```
docker compose up --build
        │
        ├── app container (port 8000)
        │       ├── /api/*   → FastAPI routes
        │       └── /*       → React 18 SPA (Vite build, served as static files)
        │
        └── postgres container (port 5432, internal only)
```

Single origin. No nginx. No CORS. One port for judges, one command for setup.

**AI extraction providers:**

| Provider | When to use | Model |
|---|---|---|
| `fixture` | Demo / offline / CI | Pre-built JSON, no API call |
| `claude` | Production primary | `claude-sonnet-4-6` |
| `gemini` | Fallback / cost-sensitive | `gemini-2.5-flash` |

All three implement the same `ExtractionProvider` interface and return an identical `ExtractedInvoice` schema. Switch providers with one env var, no code change.

**Tech stack:**
- Backend: Python 3.12, FastAPI 0.115, SQLAlchemy 2.0 + Alembic, Postgres 16, psycopg 3
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, TanStack Query v5, Zustand v4, React Router v6

---

## Slide 5 — What We Built in 48 Hours

**Title:** 48 Hours → Production-Ready Demo

**Backend (Day 1, ~14 hours)**
- JWT auth with 4-role RBAC (`platform_admin`, `firm_admin`, `accountant`, `company_user`)
- Three-tier tenant isolation enforced via a single FastAPI dependency
- Pluggable extraction subsystem: Fixture + Claude + Gemini providers
- 6 API modules: auth, transactions (upload/list/patch/submit/approve/reject), onboarding (firms/companies/payment-heads/users), reports, dashboard, health
- Full audit logging on every transaction status change
- Alembic migrations for all 8 ORM models

**Frontend (Day 1–2, ~12 hours)**
- 12 pages across 4 roles: login, upload + extraction preview, review queue, transaction detail, dashboard, firms, companies, payment heads, team, reports (list + upload), manual transaction entry
- All pages wired to real API hooks via TanStack Query — no mocked data in the UI
- Protected routes with role-based redirects, loading/empty states, toasts, form validation

**Infrastructure**
- Docker Compose: two services, one build command
- Multi-stage Dockerfile: Node 20 builds React → Python 3.12-slim serves it via StaticFiles
- Seed script: 6 demo users, 2 companies, 10 pre-staged transactions, 1 MIS report — idempotent, runs on every `make fresh`
- 8 real Indian invoice fixture JSONs (Tata Steel, BEL, DHL, L&T, SAIL, Mahindra, Bajaj, Wipro) + 1 salary register fixture

**Lines of code written from scratch:** ~4,500 Python, ~5,200 TypeScript/TSX

---

## Slide 6 — Roadmap

**Title:** Where FinBridge Goes Next

**Near-term (next sprint)**
- Live AI provider toggle in the UI — switch between Claude and Gemini without a container restart or env var change
- Bank statement reconciliation: automatically match payment transactions to accepted invoices, flag unmatched debits
- Bulk upload: drag-and-drop multiple invoices, queue them for extraction in parallel

**Mid-term**
- ERP export: push accepted transactions to Tally, Zoho Books, or QuickBooks via their APIs — eliminating re-entry on the accountant side as well
- Email notifications: notify accountants when new transactions are submitted; notify company users on approval or rejection
- GST return pre-fill: aggregate accepted invoices by GSTIN and generate GSTR-1/GSTR-2B reconciliation reports

**Infrastructure**
- Object storage (S3-compatible) for uploaded files — swap the `UPLOAD_DIR` filesystem for a MinIO or AWS S3 backend via a single provider interface
- Postgres row-level security as a second layer of tenant isolation
- Refresh token rotation and token revocation for production-grade session management

**Longer-term**
- Mobile upload via camera — OCR directly from a phone photo without needing a desktop browser
- Automated duplicate detection: flag invoices with the same vendor + invoice number + amount already in the ledger
- Multi-language extraction: Tamil, Telugu, Hindi invoice templates in addition to English
