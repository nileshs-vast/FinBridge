# FinBridge

**AI-powered financial document processing for Indian SMEs**

FinBridge lets companies upload vendor bills, invoices, and salary registers. An AI layer (Claude, Gemini, or an offline fixture provider) extracts structured transaction data in seconds. Accountants then review, edit, and approve with one click — all within a multi-tenant platform built for accounting firms serving multiple client companies.

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build
# Open http://localhost:8000
```

The container runs `alembic upgrade head` and seeds demo data automatically on first boot. To reset at any point:

```bash
make fresh      # drops volumes → rebuilds → migrates → re-seeds
```

---

## Demo Credentials

All users share the password: **`Finbridge#2026`**

| Role | Email | Firm | Company |
|---|---|---|---|
| `platform_admin` | `platform@finbridge.local` | — | — |
| `firm_admin` | `admin@sharmaco.local` | Sharma & Co. | — |
| `accountant` | `priya@sharmaco.local` | Sharma & Co. | — (reviews both companies) |
| `accountant` | `rahul@sharmaco.local` | Sharma & Co. | — (reviews both companies) |
| `company_user` | `upload@acme.local` | Sharma & Co. | Acme Manufacturing |
| `company_user` | `upload@lumenit.local` | Sharma & Co. | Lumen IT |

**Pre-seeded data (Acme Manufacturing):**
- 4 accepted invoices (Tata Steel, BEL, DHL, April salary register)
- 4 pending-review invoices (Mahindra Logistics, L&T, Bajaj Electricals, SAIL)
- 2 AI-draft invoices (Wipro Infrastructure, Ultratech Cement)
- 1 MIS report (April 2024)

---

## Key Workflows

**Company User** (`upload@acme.local`)
- Upload a document (PDF, image, Excel) from the Upload page
- Review the AI-extracted fields: vendor, invoice number, date, amount, GST breakdown, line items
- Edit any incorrect fields, assign a payment head, then submit for accountant review

**Accountant** (`priya@sharmaco.local`)
- Open the Review Queue to see all pending transactions across companies in the firm
- Open a transaction to see the document alongside extracted fields side by side
- Approve, reject, or request more information with a note

**Firm Admin** (`admin@sharmaco.local`)
- Manage companies and their payment head taxonomies under Firms
- Add or remove accountant team members
- View the firm-wide dashboard and download MIS reports

**Platform Admin** (`platform@finbridge.local`)
- Create and manage accounting firms
- Accessible at the top of the tenant hierarchy

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL username | `finbridge` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `finbridge` |
| `POSTGRES_DB` | PostgreSQL database name | `finbridge` |
| `DATABASE_URL` | Full SQLAlchemy connection string | `postgresql+psycopg://finbridge:finbridge@postgres:5432/finbridge` |
| `JWT_SECRET` | HS256 signing secret — **change in production** | `change-me-in-production-please` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes | `1440` (24 hours) |
| `UPLOAD_DIR` | Container path where uploaded files are stored | `/data/uploads` |
| `MAX_UPLOAD_BYTES` | Maximum upload size in bytes | `10485760` (10 MB) |
| `EXTRACTION_PROVIDER` | AI backend: `fixture`, `claude`, or `gemini` | `fixture` |
| `ANTHROPIC_API_KEY` | Required when `EXTRACTION_PROVIDER=claude` | _(empty)_ |
| `CLAUDE_MODEL` | Claude model identifier | `claude-sonnet-4-6` |
| `GEMINI_API_KEY` | Required when `EXTRACTION_PROVIDER=gemini` | _(empty)_ |
| `GEMINI_MODEL` | Gemini model identifier | `gemini-2.5-flash` |
| `APP_ENV` | Application environment | `development` |
| `LOG_LEVEL` | Log verbosity | `INFO` |

> **Live AI extraction:** set `EXTRACTION_PROVIDER=claude` and supply your `ANTHROPIC_API_KEY`, then `make fresh`. The fixture provider works fully offline and is the default for demos.

---

## Useful Commands

```bash
# Docker
make up              # docker compose up --build (foreground)
make down            # stop and remove containers
make logs            # tail app container logs
make ps              # show running containers
make fresh           # drop DB volume → rebuild → migrate → seed (safe, idempotent)

# Database
make migrate         # run alembic upgrade head inside the running app container
make seed            # run seed script inside the running app container
make shell-db        # open psql in the postgres container
make shell-app       # open bash in the app container

# Tests
make test            # run pytest smoke tests inside the app container

# Docker dev mode (hot-reload, source bind-mount, no SPA build needed)
make dev             # docker compose with ./backend:/app + uvicorn --reload

# Local development (fastest inner loop, needs local Postgres)
make backend-install # pip install -e ".[dev]" in backend/
make dev-backend     # uvicorn --reload on :8000
make dev-frontend    # vite dev server on :5173 (proxies /api/* to :8000)
```

---

## Architecture

FinBridge uses a three-tier tenancy model: **Platform → Accounting Firm → Company**. Every request is scoped by `firm_id` and `company_id` from the JWT — there is no Postgres RLS; the `tenant_scope()` FastAPI dependency enforces isolation at the service layer.

A single Docker container on port 8000 serves both the API and the React SPA: FastAPI handles all `/api/*` routes and mounts the built Vite output at `/` for everything else. No nginx, no CORS, no second port.

The extraction subsystem is pluggable via an `ExtractionProvider` interface:

- **Fixture** (default) — returns pre-built JSON from `backend/seeds/extractions/`; works completely offline
- **Claude** — `claude-sonnet-4-6` vision, activated by setting `EXTRACTION_PROVIDER=claude`
- **Gemini** — `gemini-2.5-flash`, activated by setting `EXTRACTION_PROVIDER=gemini`

All three providers return the same `ExtractedInvoice` Pydantic schema, so the rest of the pipeline is provider-agnostic.

---

## Intentional Scope Cuts

This is a 48-hour hackathon build. The following are known gaps, not oversights:

- No refresh tokens or token revocation (24-hour JWTs, HS256)
- File storage is local filesystem on a Docker volume, not S3 or object storage
- No email notifications (approval/rejection is in-app only)
- No Postgres row-level security (tenant isolation is enforced in application code)
- No ERP integration (Tally, Zoho Books — roadmap only)
- Smoke tests only, no unit or E2E coverage

---

## Troubleshooting

**`docker compose up` fails immediately with a database connection error**

The app container starts before Postgres is fully ready. This is handled by a healthcheck, but on slow machines the retry window can be exceeded. Run `make down && make up` to retry, or `make fresh` for a clean state.

**Login returns 422 Unprocessable Entity**

The `LoginRequest` schema expects `email` and `password` fields as a JSON body, not form data. If you are hitting the API directly with curl, pass `-H "Content-Type: application/json"`.

**Uploaded file is not recognized by the fixture provider**

The fixture provider matches files by the stem of the original filename to JSON files in `backend/seeds/extractions/`. Uploading a file named `tata_steel_invoice.pdf` will load `tata_steel_invoice.json`. Any unrecognized filename falls back to a generic extraction response.

**`make fresh` hangs at "waiting for app to be ready"**

The 5-second sleep in `make fresh` is a heuristic. If migrations or seeding fail silently, run `make logs` in another terminal to see the app output, then `make shell-app` to inspect or rerun `alembic upgrade head` and `python -m app.seeds.run` manually.

**bcrypt error on startup ("AttributeError: module 'bcrypt' has no attribute...")**

bcrypt is pinned to `4.0.1` in `pyproject.toml`. Do not upgrade it without testing `hash_password` and `verify_password`. The `passlib[bcrypt]==1.7.4` dependency is incompatible with bcrypt ≥ 4.1.

**Frontend shows stale data after re-seeding**

TanStack Query caches responses. Hard-refresh the browser (`Ctrl+Shift+R`) or clear local storage after `make fresh`.

**API docs**

OpenAPI schema: [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json)  
Swagger UI: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
