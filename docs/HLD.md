# FinBridge — High-Level Design

Operational detail for the architecture described in [ARCHITECTURE.md](./ARCHITECTURE.md). This document covers user flows, the data model, API surface, the extraction provider contract, auth, and the demo script.

---

## 1. Roles & Permissions

| Role | Tenancy scope | Permissions |
|---|---|---|
| `platform_admin` | Global | Create / list firms; create firm admins |
| `firm_admin` | One firm | Create / list companies in firm; create accountants; configure payment heads + sub-heads per company; create company users |
| `accountant` | One firm | View review queue across all companies in firm; edit / approve / reject transactions; upload reports to companies |
| `company_user` | One company | Upload transactions (invoice / payment / salary register); view own company's accepted transactions; download MIS reports |

Roles are flat. Role + (firm_id, company_id) tuple is sufficient for every authorization decision in this system.

---

## 2. Core User Flows

### 2.1 Onboarding chain (top-down)

```
Platform Admin                Firm Admin                Company User
     │                            │                          │
     │── POST /firms ────────────▶│                          │
     │   {name, admin_email,      │                          │
     │    admin_password}         │                          │
     │                            │── POST /companies ──────▶│
     │                            │   {name, business_type,  │
     │                            │    admin_email,          │
     │                            │    admin_password}       │
     │                            │                          │
     │                            │── POST /payment-heads ──▶│
     │                            │   (or apply template)    │
     │                            │                          │
     │                            │── POST /users           │
     │                            │   {role: accountant,     │
     │                            │    firm_id}              │
     │                            │                          │
     │                            │── POST /users           │
     │                            │   {role: company_user,   │
     │                            │    company_id}           │
```

For the hackathon, the bulk of this chain is **seeded** before the demo. The UI only needs to demonstrate one create flow at each tier to satisfy the "onboarding flow across all three tenancy levels" requirement.

### 2.2 Upload → Extract → Review (the core demo)

```
Company User                       Backend                            Accountant
     │                                │                                   │
     │── POST /transactions/upload ──▶│                                   │
     │   multipart: file              │                                   │
     │   form: transaction_type,      │                                   │
     │         direction              │                                   │
     │                                │── save file to /data/uploads      │
     │                                │── ExtractionProvider.extract()    │
     │                                │── INSERT transaction              │
     │                                │   status=draft_ai                 │
     │                                │── INSERT attachment               │
     │                                │── audit_log(uploaded)             │
     │                                │                                   │
     │◀── 200 { transaction, extracted } ─────────────────────────────────│
     │                                │                                   │
     │── PATCH /transactions/{id} ───▶│ (user edits fields)               │
     │   status=pending_review        │                                   │
     │                                │── audit_log(submitted)            │
     │                                │                                   │
     │                                │◀────── GET /transactions ─────────│
     │                                │        ?status=pending_review     │
     │                                │                                   │
     │                                │◀────── PATCH /transactions/{id} ──│
     │                                │        (accountant edits)         │
     │                                │                                   │
     │                                │◀────── POST /transactions/{id}/   │
     │                                │        approve  | reject          │
     │                                │── audit_log(accepted | rejected)  │
     │                                │── status=accepted | rejected      │
```

### 2.3 Reports

```
Accountant                          Backend                         Company User
     │                                  │                                │
     │── POST /reports ────────────────▶│                                │
     │   multipart: file                │                                │
     │   form: title, company_id        │                                │
     │                                  │── save file                    │
     │                                  │── INSERT report                │
     │                                  │── audit_log(report_uploaded)   │
     │                                  │                                │
     │                                  │◀────── GET /reports ───────────│
     │                                  │        (scoped to company)     │
     │                                  │                                │
     │                                  │◀────── GET /reports/{id}/file ─│
```

---

## 3. API Surface

All endpoints under `/api`. Authentication: `Authorization: Bearer <jwt>` on every route except `/api/auth/login`.

### Auth
| Method | Path | Body / Query | Returns |
|---|---|---|---|
| POST | `/auth/login` | `{email, password}` | `{access_token, user}` |
| GET | `/auth/me` | — | Current user object |

### Platform Admin
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/firms` | — | List all firms |
| POST | `/firms` | `{name, admin_email, admin_password}` | Creates firm + firm_admin user atomically |

### Firm Admin
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/companies` | — | Scoped to firm |
| POST | `/companies` | `{name, business_type, admin_email, admin_password}` | Creates company + first company_user atomically; applies default payment-head template by business_type |
| GET | `/companies/{id}/payment-heads` | — | Returns tree (heads + sub-heads) |
| POST | `/companies/{id}/payment-heads` | `{name, parent_head_id?}` | Add a head or sub-head |
| GET | `/users?role=accountant` | — | List firm's accountants |
| POST | `/users` | `{role: accountant, email, password}` | Add accountant |
| POST | `/users` | `{role: company_user, email, password, company_id}` | Add company user |

### Transactions
| Method | Path | Body / Query | Notes |
|---|---|---|---|
| POST | `/transactions/upload` | multipart `file` + form `transaction_type`, `direction?`, `company_id?` | Triggers AI extraction for `invoice`; returns draft transaction |
| POST | `/transactions/manual` | `{transaction_type, direction, vendor, amount, date, payment_head_id, ...}` | Manual entry path for non-invoice types |
| GET | `/transactions` | `?status=&type=&company_id=` | Tenant-scoped list |
| GET | `/transactions/{id}` | — | Includes attachments + raw extraction JSON |
| PATCH | `/transactions/{id}` | Partial fields | Update; allowed in `draft_ai`, `pending_review`, and `needs_info` only |
| POST | `/transactions/{id}/submit` | — | Move `draft_ai` or `needs_info` → `pending_review`; returns `possible_duplicate_of` if a match is found |
| POST | `/transactions/{id}/approve` | — | Accountant only |
| POST | `/transactions/{id}/reject` | `{reason}` | Accountant only |
| POST | `/transactions/{id}/request-info` | `{reason}` | Accountant returns transaction to `needs_info`; company user can edit and resubmit |
| GET | `/transactions/{id}/attachment` | — | Streams original file |

### Reports
| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/reports` | `?company_id=` | Company users see own; accountants see company-scoped |
| POST | `/reports` | multipart `file` + form `title`, `company_id` | Accountant uploads |
| GET | `/reports/{id}/file` | — | Streams file |

### Dashboard
| Method | Path | Returns |
|---|---|---|
| GET | `/dashboard/summary` | Counts, top expense heads, last 10 transactions — scoped to caller |

---

## 4. Data Model

All timestamps are `TIMESTAMP WITH TIME ZONE`. Primary keys are UUID v4 unless noted. ISO 8601 / RFC 3339 throughout. All synthetic field names; no production data referenced.

### `firms`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | TEXT NOT NULL | |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

### `companies`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `firm_id` | UUID FK → firms.id | INDEX |
| `name` | TEXT NOT NULL | |
| `business_type` | TEXT NOT NULL | `manufacturing` / `it` / `services` |
| `created_at` | TIMESTAMPTZ | |

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `email` | CITEXT UNIQUE NOT NULL | |
| `password_hash` | TEXT NOT NULL | bcrypt |
| `role` | TEXT NOT NULL | `platform_admin`/`firm_admin`/`accountant`/`company_user` |
| `firm_id` | UUID FK NULLABLE | required for firm_admin, accountant, company_user |
| `company_id` | UUID FK NULLABLE | required for company_user |
| `created_at` | TIMESTAMPTZ | |

### `payment_heads`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → companies.id | INDEX |
| `name` | TEXT NOT NULL | |
| `parent_head_id` | UUID FK → payment_heads.id NULLABLE | self-ref for sub-heads |
| `created_at` | TIMESTAMPTZ | |
| UNIQUE | (`company_id`, `parent_head_id`, `name`) | |

### `transactions`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → companies.id | INDEX |
| `transaction_type` | TEXT NOT NULL | `invoice`/`payment`/`salary_register`/`bank_statement` |
| `direction` | TEXT NULLABLE | `purchase`/`sales`/`payment_in`/`payment_out` |
| `vendor` | TEXT NULLABLE | |
| `invoice_no` | TEXT NULLABLE | |
| `transaction_date` | DATE NULLABLE | |
| `amount` | NUMERIC(14,2) NULLABLE | |
| `currency` | TEXT DEFAULT 'INR' | ISO 4217 |
| `payment_head_id` | UUID FK NULLABLE | |
| `status` | TEXT NOT NULL | `draft_ai`/`pending_review`/`needs_info`/`accepted`/`rejected` |
| `raw_extraction` | JSONB NULLABLE | Full `ExtractedInvoice` response |
| `notes` | TEXT NULLABLE | accountant remarks |
| `rejection_reason` | TEXT NULLABLE | |
| `info_request_reason` | TEXT NULLABLE | populated when accountant returns the transaction with `needs_info` |
| `possible_duplicate_of` | UUID FK transactions.id NULLABLE | set on submit if a likely duplicate accepted transaction exists for `(company_id, vendor, invoice_no)` |
| `uploaded_by` | UUID FK users.id | |
| `reviewed_by` | UUID FK users.id NULLABLE | |
| `created_at` | TIMESTAMPTZ | |
| `reviewed_at` | TIMESTAMPTZ NULLABLE | |

### `attachments`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `transaction_id` | UUID FK → transactions.id ON DELETE CASCADE | |
| `file_path` | TEXT NOT NULL | relative to UPLOAD_DIR |
| `mime_type` | TEXT NOT NULL | |
| `original_name` | TEXT NOT NULL | |
| `size_bytes` | BIGINT NOT NULL | |
| `created_at` | TIMESTAMPTZ | |

### `reports`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK | INDEX |
| `title` | TEXT NOT NULL | |
| `file_path` | TEXT NOT NULL | |
| `mime_type` | TEXT NOT NULL | |
| `original_name` | TEXT NOT NULL | |
| `uploaded_by` | UUID FK users.id | accountant |
| `created_at` | TIMESTAMPTZ | |

### `audit_log`
| Column | Type | Notes |
|---|---|---|
| `id` | BIGSERIAL PK | |
| `actor_user_id` | UUID FK users.id | |
| `action` | TEXT NOT NULL | e.g. `transaction.upload`, `transaction.approve`, `report.upload` |
| `entity_type` | TEXT NOT NULL | |
| `entity_id` | UUID NOT NULL | |
| `payload` | JSONB | optional context |
| `created_at` | TIMESTAMPTZ DEFAULT now() | |

### Indexes (Day-1 minimum)
- `companies(firm_id)`
- `users(firm_id)`, `users(company_id)`, `users(email)` UNIQUE
- `payment_heads(company_id)`, `payment_heads(parent_head_id)`
- `transactions(company_id, status)`, `transactions(company_id, created_at DESC)`
- `attachments(transaction_id)`
- `reports(company_id)`
- `audit_log(entity_type, entity_id)`

---

## 5. ExtractionProvider Contract

### Pydantic schema (`extraction/schema.py`)

```python
class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float
    hsn_sac: str | None = None             # India: HSN code (goods) or SAC code (services)

class ExtractedInvoice(BaseModel):
    vendor: str | None
    vendor_address: str | None = None
    vendor_gstin: str | None = None        # India: 15-char vendor GST identification number
    customer_gstin: str | None = None      # India: buyer's GSTIN if visible on the bill
    place_of_supply: str | None = None     # India: state code; drives IGST vs CGST+SGST split
    invoice_no: str | None
    invoice_date: date | None
    due_date: date | None = None
    currency: str = "INR"
    subtotal: float | None = None
    tax_amount: float | None = None        # total tax = cgst + sgst + igst
    cgst: float | None = None              # Central GST (intra-state supply)
    sgst: float | None = None              # State GST (intra-state supply)
    igst: float | None = None              # Integrated GST (inter-state supply)
    reverse_charge: bool = False           # India: reverse-charge mechanism flag
    total: float | None
    line_items: list[LineItem] = []
    suggested_direction: Literal["purchase", "sales"] | None = None
    confidence: dict[str, float] = {}      # field_name → 0.0–1.0
    notes: str | None = None               # AI-surfaced caveats
```

**Note on GST fields:** these are nullable so non-Indian invoices (or invoices where GST details are illegible) extract cleanly. Demo fixtures populate them for Indian seed bills.

### Protocol (`extraction/base.py`)

```python
class ExtractionProvider(Protocol):
    name: str
    async def extract(
        self,
        file_path: Path,
        mime_type: str,
    ) -> ExtractedInvoice: ...
```

### Provider selection
At app startup, `app.extraction.factory.build_provider(settings)` returns one instance based on `EXTRACTION_PROVIDER`:

- `fixture` (default) → `FixtureProvider(seeds_dir="seeds/extractions/")`. Looks up extracted JSON by the original filename's SHA-256 (or filename if found). Falls back to a generic mock for unseeded files.
- `claude` → `ClaudeProvider(api_key=..., model="claude-sonnet-4-6")`. Uses Anthropic SDK with tool-use; the tool definition mirrors `ExtractedInvoice`'s JSON schema. PDFs sent as `document` blocks; images as `image` blocks.
- `gemini` → `GeminiProvider(api_key=..., model="gemini-2.5-flash")`. Uses `responseSchema` parameter for structured output.

### Failure handling
All providers raise `ExtractionError(message, retryable: bool)` on failure. The transaction service catches it, persists the transaction with `status=draft_ai` and `raw_extraction = {"error": …}`, and returns an empty `ExtractedInvoice` so the company user can fill fields manually. The UI shows a banner: "AI extraction unavailable — please enter fields manually."

---

## 6. Auth Flow

### Token contents
```
{
  "sub": "<user.id>",
  "role": "company_user",
  "firm_id": "<uuid|null>",
  "company_id": "<uuid|null>",
  "iat": 1719... ,
  "exp": 1719...   // iat + 24h
}
```

### Dependency chain
```
get_db                    →   SQLAlchemy session
current_user(get_db)      →   decodes JWT, loads user, raises 401 on fail
require_role(*roles)      →   factory; 403 if user.role not in roles
tenant_scope(current_user) →  returns TenantContext(firm_id, company_id)
```

Service functions accept `TenantContext` as a parameter and apply it to every query:

```python
def list_transactions(db, ctx: TenantContext, **filters):
    q = db.query(Transaction).filter(Transaction.company_id.in_(ctx.allowed_companies))
    ...
```

`ctx.allowed_companies` resolution by role:
- `platform_admin` → all companies (rarely needed; usually not transaction-scoped)
- `firm_admin` / `accountant` → all companies belonging to `ctx.firm_id`
- `company_user` → `[ctx.company_id]`

---

## 7. Frontend — Page Map

| Path | Role | Purpose |
|---|---|---|
| `/login` | public | Login form |
| `/platform/firms` | platform_admin | List + create firm (modal) |
| `/firm/companies` | firm_admin | List + create company |
| `/firm/companies/:id/payment-heads` | firm_admin | View / add heads + sub-heads |
| `/firm/team` | firm_admin | List + add accountants |
| `/company/upload` | company_user | Drag-drop bill, see extraction preview, edit, submit |
| `/company/transactions` | company_user | History (accepted / rejected / in-review) |
| `/company/reports` | company_user | List + download MIS reports |
| `/accountant/queue` | accountant | Pending-review queue (cards or table) |
| `/accountant/transactions/:id` | accountant | Side-by-side: original file + editable form + approve/reject |
| `/accountant/reports` | accountant | Upload report for a company |
| `/dashboard` | any | Counts, recent activity, top expense heads |

Routing guards: a `<RequireRole roles=["accountant","firm_admin"]>` wrapper around protected routes. Auth state in Zustand with localStorage persistence.

---

## 8. Seed Data

`backend/app/seeds/seed.py` is idempotent and creates:

| Entity | Count | Notes |
|---|---|---|
| Platform admin | 1 | `platform@finbridge.local` / `Finbridge#2026` |
| Accounting firms | 1 | "Sharma & Co." |
| Firm admin | 1 | `admin@sharmaco.local` |
| Accountants | 2 | `priya@sharmaco.local`, `rahul@sharmaco.local` |
| Companies | 2 | "Acme Manufacturing" (manufacturing), "Lumen IT" (it) |
| Payment-head templates | 3 | Manufacturing / IT / Services, each with 2-level structure |
| Company users | 2 | one per company |
| Demo bills (in `seeds/bills/`) | 8 | 5 clean invoices, 2 messy, 1 salary register CSV |
| Demo extractions (in `seeds/extractions/`) | 8 | matched 1:1 by filename hash for FixtureProvider |
| Pre-staged transactions | ~10 | mix of `draft_ai`, `pending_review`, `accepted` to populate dashboard |
| Pre-staged MIS report | 1 | PDF attached to Acme |

All demo passwords printed at end of seed for the README.

### Payment-head templates (synthetic)

```
manufacturing:
  - Raw Materials
      - Steel
      - Plastic
  - Utilities
      - Electricity
      - Water
  - Logistics
      - Transport
      - Warehousing

it:
  - Salaries
      - Engineering
      - Operations
  - Infrastructure
      - Cloud
      - Software Licenses
  - Office
      - Rent
      - Internet

services:
  - Salaries
      - Consultants
      - Admin
  - Travel
      - Local
      - International
  - Marketing
      - Digital
      - Events
```

---

## 9. Demo Script (4 scenes, ~3 minutes)

> Recorded twice. Once for the submission video, once as backup screenshots.

### Scene 1 — The hierarchy (30s)
Login as platform admin → show firms list → click into Sharma & Co. (read-only). Log out. Login as firm admin → show companies (Acme Manufacturing, Lumen IT), payment heads tree, accountants list.

### Scene 2 — The AI moment (60s)
Switch to company user (`upload@acme.local`). Drag a messy phone-photo invoice into the upload zone. **Watch the form fill in** with vendor, invoice number, date, line items, total. Tweak one field. Submit for review.

### Scene 3 — The review (45s)
Switch to accountant (`priya@sharmaco.local`). New item appears at the top of the queue. Open it — original file on the left, editable form on the right with confidence indicators. Confirm payment head ("Raw Materials → Steel"). Approve.

### Scene 4 — The loop closes (30s)
Switch back to company user. Dashboard updates: counts increment, the transaction shows under accepted, top-expense chart redraws. Open Reports tab → download the MIS report Priya pre-uploaded.

### Closing line for the deck
"Three roles, one workflow, AI doing the data entry. Built in 48 hours."

---

## 10. Error & Edge Cases (handled)

| Case | Behavior |
|---|---|
| Upload non-image, non-PDF file | 400 with friendly message; UI shows allowed types |
| File over 10 MB | 413; UI shows size limit |
| AI extraction failure / timeout | Transaction persists with empty fields + error in `raw_extraction`; UI banner; user can fill manually |
| Accountant approves while company user is editing | Server uses last-write-wins on PATCH; approve transitions only allowed from `pending_review` (409 otherwise) |
| Cross-tenant access attempt | 403 enforced by service-layer filter |
| Token expired | 401 → frontend redirects to `/login`, preserves intended destination |
| Concurrent reject + approve | First write wins; second returns 409 with current status |
| Seed re-run | Idempotent: `INSERT … ON CONFLICT DO NOTHING` on natural keys (email, name+firm) |

---

## 11. What's intentionally absent

- Pagination on list endpoints (small dataset; LIMIT 100 is enough)
- Search/filter UI beyond `?status=`
- WebSockets / live updates (TanStack Query refetch on focus suffices)
- Soft deletes
- Versioning of transactions (audit log is the history)
- Email sending of any kind
- Background jobs / Celery / RQ (extraction is awaited inline; acceptable for demo loads)

---

## 12. References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system structure, tech choices, ADRs
- `FinBridge_Hackathon_Problem_Statement.pdf` — original problem statement
