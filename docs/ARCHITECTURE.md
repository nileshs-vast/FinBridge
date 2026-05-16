# FinBridge — Architecture

A multi-tenant financial data exchange platform built for a 48-hour hackathon. This document describes the system structure, technology choices, and the reasoning behind them.

---

## 1. Context

Mid-sized businesses exchange financial information with their accounting firms over email, WhatsApp, and shared drives. FinBridge replaces that with a structured SaaS workflow in which:

- **Companies** upload bills, payments, salary registers
- **Claude vision** auto-extracts the data into structured transaction records
- **Accountants** review, refine, and accept
- **MIS reports** flow back to the company

The platform is three-tier multi-tenant: **Platform → Accounting Firm → Company**.

---

## 2. Goals & Non-Goals

### In scope (must work)
- 3-tier tenancy with role-based access
- Configurable payment heads + sub-heads per company
- File upload (invoices, payments, salary register)
- AI-powered bill scanning with editable preview
- Accountant review queue (edit / approve / reject)
- Reports upload by accountant, download by company
- One-command Docker deployment

### Explicitly out of scope
- Zoho / QuickBooks / Tally integration (roadmap slide only)
- Payment gateway integration
- Production-grade auth (password reset, MFA, refresh tokens, email verification)
- Advanced reporting engine
- Postgres row-level security
- Mobile / PWA (stretch only)
- Frontend unit tests, E2E tests

---

## 3. Tech Stack & Reasoning

| Layer | Choice | Why |
|---|---|---|
| Backend | **FastAPI** | Async, automatic OpenAPI (frees the frontend from manual API typing), Pydantic for clean schemas, well-supported by Claude Code generation. Django was rejected for SPA-auth friction and ORM ceremony. |
| ORM + migrations | **SQLAlchemy 2.0 + Alembic** | Mature, standard, deterministic migrations. |
| Database | **PostgreSQL 16** | Required by prompt. JSONB for raw AI extraction blobs. |
| Auth | **JWT** with `user_id`, `role`, `firm_id`, `company_id` claims | Stateless, no Redis/session store, fits SPA. 24-hour access tokens, no refresh tokens — acceptable for demo. |
| File storage | **Local filesystem on Docker volume** | Prompt specifies local-only. MinIO would be production-correct but burns time we don't have. |
| AI extraction | **`ExtractionProvider` interface** with `Fixture`, `Claude`, `Gemini` impls | Demo runs offline via Fixture; Claude is the documented primary; Gemini is fallback when no Anthropic key is available. |
| Frontend | **Vite + React 18 + TypeScript + Tailwind + shadcn/ui** | shadcn delivers production-feel UX without designing from scratch — directly serves the 15% polish bucket. |
| Frontend state | **TanStack Query** for server state, **Zustand** for auth/user | No Redux ceremony. |
| Frontend routing | **React Router v6** | Standard. |
| Deployment | **docker-compose** (2 services: `app` + `postgres`) | FastAPI serves the built React SPA as static assets — single origin, no CORS, no nginx, one port for judges. |
| Tests | **Minimal smoke tests** on critical endpoints | Hackathon judges score demos, not coverage. Honest tradeoff documented in README. |

---

## 4. System Topology

```
┌──────────────────────────────────────────────────────────────┐
│                       docker-compose                         │
│                                                              │
│   ┌──────────────────────────┐    ┌───────────────────────┐  │
│   │       app (8000)         │    │   postgres (5432)     │  │
│   │                          │◀──▶│                       │  │
│   │  FastAPI                 │    │  finbridge DB         │  │
│   │   ├─ /api/*  → routes    │    │  volume: pgdata       │  │
│   │   └─ /*      → React SPA │    └───────────────────────┘  │
│   │                          │                               │
│   │  volume: ./data/uploads ─┼──▶ /data/uploads              │
│   └──────────┬───────────────┘                               │
└──────────────┼───────────────────────────────────────────────┘
               │
               ▼
       ExtractionProvider (in-process)
        ├─ FixtureProvider  (default, no key required)
        ├─ ClaudeProvider   (if ANTHROPIC_API_KEY set)
        └─ GeminiProvider   (if GEMINI_API_KEY set)
```

One port exposed to the host (8000). Judges run `cp .env.example .env && docker compose up --build` and hit `http://localhost:8000`.

---

## 5. Component Breakdown

### Backend (`backend/`)

```
backend/
├── app/
│   ├── api/                  # FastAPI route modules, one per resource
│   │   ├── auth.py
│   │   ├── firms.py
│   │   ├── companies.py
│   │   ├── users.py
│   │   ├── payment_heads.py
│   │   ├── transactions.py
│   │   ├── reports.py
│   │   └── dashboard.py
│   ├── core/
│   │   ├── config.py         # pydantic-settings
│   │   ├── security.py       # JWT issue/verify, password hashing
│   │   └── deps.py           # FastAPI dependencies: get_db, current_user, tenant_scope
│   ├── db/
│   │   ├── base.py           # SQLAlchemy Base + session
│   │   └── models.py         # ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # Business logic (transaction service, report service, audit)
│   ├── extraction/           # Provider interface + implementations
│   │   ├── base.py           # ExtractionProvider protocol
│   │   ├── fixture.py
│   │   ├── claude.py
│   │   ├── gemini.py
│   │   └── schema.py         # ExtractedInvoice Pydantic model
│   ├── seeds/                # Seed script + demo bills + fixture extractions
│   ├── static/               # Built React app (mounted at /)
│   └── main.py
├── alembic/
├── tests/                    # Smoke tests only
├── pyproject.toml
└── Dockerfile
```

### Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── platform/         # Platform admin: list/create firms
│   │   ├── firm/             # Firm admin: companies, accountants, payment heads
│   │   ├── company/          # Company user: upload, history
│   │   ├── accountant/       # Review queue, transaction detail
│   │   └── reports/
│   ├── components/           # UI (shadcn-based)
│   ├── api/                  # Typed API client (axios)
│   ├── lib/                  # auth store (Zustand), router guards, query client
│   ├── routes.tsx
│   └── main.tsx
├── public/
├── vite.config.ts
├── package.json
└── Dockerfile                # multi-stage: build → copies dist/ into backend image
```

### Deployment (`/`)

```
docker-compose.yml
.env.example
Makefile                      # up / down / seed / logs / fresh
seeds/
  bills/                      # PDFs and images for demo
  extractions/                # matching JSON for FixtureProvider
README.md
docs/
  ARCHITECTURE.md
  HLD.md
```

---

## 6. Multi-Tenancy Model

**Shared schema, application-enforced tenant isolation.**

- Every tenant-scoped table carries `firm_id` and/or `company_id` columns.
- JWTs encode `firm_id` and `company_id` for non-platform users.
- A FastAPI dependency `tenant_scope()` extracts these from the JWT and is required on every protected route.
- Service layer functions accept a `TenantContext` and apply `WHERE firm_id = :firm AND company_id = :company` filters.
- One smoke test verifies cross-tenant access returns 403.

**Honest gap:** no Postgres row-level security. If app-layer filtering is bypassed, isolation breaks. Documented in the "next steps" slide as RLS hardening.

---

## 7. Data Model (overview)

Full schema in [HLD.md §4](./HLD.md#4-data-model). High-level entity map:

```
firms ──┬── users (firm_admin, accountant)
        └── companies ──┬── users (company_user)
                        ├── payment_heads (self-referencing for sub-heads)
                        ├── transactions ── attachments
                        │                ── audit_log entries
                        └── reports
```

Critical schema decisions:
- `transactions.transaction_type` enum: `invoice | payment | salary_register | bank_statement`
- `transactions.direction`: `purchase | sales | payment_in | payment_out | null`
- `transactions.status`: `draft_ai | pending_review | accepted | rejected`
- `transactions.raw_extraction` JSONB column stores the AI's full response for audit
- `payment_heads.parent_head_id` self-reference enables sub-heads

---

## 8. AI Extraction Architecture

The AI capability is judged at 25% of total score. Treated as a first-class subsystem.

```
POST /api/transactions/upload
        │
        ▼
  TransactionService.upload()
        │
        ├──▶ persist file to /data/uploads
        │
        ├──▶ ExtractionProvider.extract(file_path, mime_type) ──┐
        │                                                       │
        │   ┌───────────────────────────────────────────────┐   │
        │   │ Selected at startup via EXTRACTION_PROVIDER:  │   │
        │   │  fixture → returns seeded JSON by filename    │◀──┘
        │   │  claude  → claude-sonnet-4-6 vision           │
        │   │  gemini  → gemini-2.5-flash                   │
        │   │  All return ExtractedInvoice (Pydantic)       │
        │   └───────────────────────────────────────────────┘
        │
        ├──▶ persist transaction with status=draft_ai
        │
        └──▶ return draft for user edit
```

### Why a provider interface
- **Demo reliability** — Fixture provider guarantees the demo works without any API key.
- **Spec fidelity** — Claude is the documented primary, matching the problem statement.
- **Fallback** — Gemini covers environments where Anthropic access isn't available.
- **Testability** — Fixture provider is also the test stub.

### Structured output strategy
Each provider returns the same `ExtractedInvoice` Pydantic model (vendor, invoice_no, date, line_items, total, currency, confidence per field). The Claude implementation uses tool-use to force schema compliance; the Gemini implementation uses Gemini's structured output mode. Schema is defined once in `extraction/schema.py`.

---

## 9. Deployment

### Composition
- `app` — Python 3.12 base; multi-stage build copies the Vite production bundle into `app/static/`. Runs `alembic upgrade head` on entrypoint before `uvicorn`.
- `postgres` — Postgres 16-alpine with named `pgdata` volume and a healthcheck (`pg_isready`).
- One bind-mount: `./data/uploads:/data/uploads`.

### Environment
Single `.env` at the repo root, generated from `.env.example`. Variables:

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Postgres DSN |
| `JWT_SECRET` | Token signing key |
| `EXTRACTION_PROVIDER` | `fixture` (default) / `claude` / `gemini` |
| `ANTHROPIC_API_KEY` | Optional; activates Claude provider |
| `CLAUDE_MODEL` | Default `claude-sonnet-4-6` |
| `GEMINI_API_KEY` | Optional; activates Gemini provider |
| `GEMINI_MODEL` | Default `gemini-2.5-flash` |
| `UPLOAD_DIR` | Default `/data/uploads` |

### One-command run (target judge experience)
```bash
cp .env.example .env
docker compose up --build
# wait for "Uvicorn running on http://0.0.0.0:8000"
# open http://localhost:8000
# login with seeded credentials (see README)
```

### Makefile targets
- `make up` — build + start
- `make seed` — run seed script (idempotent)
- `make logs` — tail app logs
- `make fresh` — drop volumes, rebuild, reseed (demo reset)

---

## 10. Architecture Decision Records (ADRs)

| # | Decision | Alternatives considered | Reason chosen | Tradeoffs accepted |
|---|---|---|---|---|
| 1 | Shared-schema multi-tenancy | Schema-per-tenant, DB-per-tenant, Postgres RLS | Lowest operational cost; sufficient for hackathon scope | DB layer doesn't enforce isolation — application-only |
| 2 | JWT auth, no refresh tokens | Session cookies, OAuth, Auth0 | Stateless, SPA-friendly, no infra | No revocation, no MFA; 24h token lifetime |
| 3 | FastAPI over Django | Django + DRF, Flask | Async, Pydantic, OpenAPI, Claude-Code-friendly | Manual wiring of admin/auth |
| 4 | Local filesystem for uploads | MinIO, S3, GridFS | Prompt says local-only; simplest | Not horizontally scalable |
| 5 | FastAPI serves static React | Separate nginx, two ports + CORS | Single origin, single container, no CORS | Couples deployment of front + back |
| 6 | `ExtractionProvider` interface | Direct Anthropic SDK calls | Demo runs offline; multi-vendor optionality | Small abstraction overhead |
| 7 | Fixture provider as default | Always-live Claude calls | Demo works without keys; deterministic | Live extraction is opt-in via env var |
| 8 | 4 roles (collapse `company_admin` into `company_user`) | 5 distinct roles | Problem statement bundles them; less branching | No in-company role hierarchy |
| 9 | Vite + Tailwind + shadcn frontend | CRA, MUI, Chakra | Fastest path to production-feel UX | Tailwind class verbosity |
| 10 | Minimal admin UI; seed most tenancy data | Full admin CRUD | Admin CRUD is not what judges score | Re-onboarding requires re-running seed |
| 11 | Smoke tests only | TDD with 80% coverage | Time budget; demo is the deliverable | Regression risk; documented |

---

## 11. Security Posture (honest)

- Passwords: bcrypt hashes (passlib).
- JWT signed with HS256; secret from env.
- All non-auth routes require `Authorization: Bearer …`.
- Tenant isolation enforced in service layer; **not** at DB layer.
- File uploads: server-side MIME validation, size limits, randomized stored filenames, originals retained in `attachments.original_name`.
- CORS: not needed (single origin).
- Not implemented: rate limiting, CSRF (SPA + bearer tokens), content-security-policy, audit-log tamper protection.

---

## 12. Known Limitations & Roadmap

Documented for the "what you'd build next" slide:

- **Production multi-tenancy** — Postgres row-level security policies per tenant.
- **Integration adapters** — Zoho / QuickBooks / Tally connectors (out of scope per prompt).
- **Auth hardening** — refresh tokens, password reset, MFA, email verification.
- **File storage** — move to S3/MinIO with presigned uploads.
- **Mobile** — PWA for company users to upload bills on the go.
- **Bulk bank statements** — auto-categorization with LLM-assisted classification against payment heads.
- **Notifications** — email + in-app on transaction state changes.
- **Dashboard depth** — cash-flow trends, aged payables, expense head drill-down.
- **Audit-log UI** — currently backend-only; surface to firm admin.

---

## 13. References

- [HLD.md](./HLD.md) — flows, schemas, API surface, demo script
- `FinBridge_Hackathon_Problem_Statement.pdf` — original problem statement
