# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

FinBridge is a 48-hour hackathon project — a multi-tenant SaaS that lets companies upload financial documents (bills, payments, salary registers), runs Claude/Gemini vision over them to extract structured transactions, and routes the drafts to an accountant for review/approval.

**Demo-first build.** [`docs/PLAN.md`](./docs/PLAN.md) is the source of truth for build order and is organized in time-boxed blocks (e.g. "Block 1-2.5", "Block 3-5"). The upload→extract→review path must work end-to-end by hour 14 (M3 gate); polish happens after. [`docs/PLAN.md` §5](./docs/PLAN.md) lists the explicit cut order if behind — do not improvise scope cuts.

**Current state (as of 2026-05-16):** Blocks 1-22 (all Day 1 + Day 2 through Block 22) are complete:
- **Backend**: All APIs (auth, transactions, onboarding, reports, dashboard), extraction subsystem (fixture/claude/gemini), all services with full audit logging — no stubs.
- **Frontend**: Full scaffold + all pages (login, upload, queue, transaction detail, dashboard, firms, companies, payment-heads, team, reports, manual transaction entry) — all wired to API hooks.
- **Seed script**: `backend/app/seeds/run.py` — idempotent; creates 6 demo users, 2 companies, payment-head templates, 10 pre-staged transactions, 1 MIS report. Run via `make seed`.
- **Fixture extractions**: `backend/seeds/extractions/` — 8 Indian invoice JSONs for the FixtureProvider demo upload flow.

**All blocks complete.** The project is submission-ready: Docker multi-stage build works (`make up`), 16/16 smoke tests green (`make test`), README complete, 7-slide presentation at `docs/presentation.html` (PDF at `docs/presentation.pdf`), demo script at `docs/demo_script.md`. Any future work is polish or bug-fixing only.

## Architecture essentials

Read [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full picture (ADRs in §10). The non-obvious things to internalize before writing code:

- **Three-tier tenancy: Platform → Firm → Company.** Every tenant-scoped table carries `firm_id` and/or `company_id`. JWTs encode `user_id`, `role`, `firm_id`, `company_id`. A single FastAPI dependency `tenant_scope()` (lives in `app/core/deps.py`) is **required on every protected route** and applies the `WHERE firm_id = :firm AND company_id = :company` filter at the service layer. There is **no Postgres RLS** — if a route bypasses `tenant_scope()`, isolation breaks. `tests/test_auth.py::test_cross_tenant_isolation` verifies cross-tenant access returns empty scope; don't remove it.
- **Single origin, single port.** FastAPI serves the built React SPA from `backend/app/static/` in production. No nginx, no CORS, port 8000 only. In dev, Vite on 5173 proxies `/api/*` to FastAPI on 8000 — frontend code always calls `/api/...` verbatim, never a `baseURL` env switch. See [`frontend/README.md`](./frontend/README.md) for the proxy plan.
- **Extraction is pluggable.** `app/extraction/base.py` defines `ExtractionProvider`; `fixture` (default), `claude`, and `gemini` implementations all return the same `ExtractedInvoice` Pydantic model. `EXTRACTION_PROVIDER=fixture` makes the demo work offline without any API key — keep it that way. Live providers are opt-in.
- **Roles are collapsed to 4:** `platform_admin`, `firm_admin`, `accountant`, `company_user` (no separate `company_admin` — ADR-8). Adding a fifth role is out of scope.
- **JWT auth, no refresh tokens, no revocation.** 24h access tokens, HS256, `JWT_SECRET` from env. Acceptable for demo; documented as a known gap.
- **Local filesystem for uploads** (`/data/uploads` in the container, bind-mounted to `./data/uploads`). MIME validated, size capped via `MAX_UPLOAD_BYTES`, stored with randomized names; original filename kept in `attachments.original_name`.
- **Transactions enums** (live in `app/db/models.py`): `transaction_type ∈ {invoice, payment, salary_register, bank_statement}`, `direction ∈ {purchase, sales, payment_in, payment_out, null}`, `status ∈ {draft_ai, pending_review, needs_info, accepted, rejected}`. AI's full response is persisted to `transactions.raw_extraction` (JSONB).

## Tech stack constraints

Python 3.12 · FastAPI 0.115 · SQLAlchemy 2.0 + Alembic · Postgres 16 · psycopg 3 · pydantic-settings · passlib[bcrypt] · python-jose. Frontend: Vite + React 18 + TypeScript + Tailwind + shadcn/ui + TanStack Query v5 + Zustand v4 + React Router v6. **Don't introduce alternatives** (no Redux, no MUI, no Django, no MinIO) — these choices are reasoned in `docs/ARCHITECTURE.md §10` and the tradeoffs are intentional for the 48-hour budget.

## Common commands

```bash
cp .env.example .env

# Docker (matches the demo path)
make up                          # build + foreground
docker compose up --build -d     # detached
make logs                        # tail app
make down

# Tests
make test                                  # pytest inside running container
docker compose run --rm app pytest         # one-shot, no `make up` first
docker compose run --rm app pytest tests/test_health.py::test_health_ok  # single test
cd backend && pytest                       # local (Python 3.12 venv)

# Local dev (faster inner loop)
make backend-install             # pip install -e ".[dev]" in backend/
make dev-backend                 # uvicorn --reload on :8000
make dev-frontend                # vite on :5173 (proxies /api/* → :8000)

# DB / migrations (Alembic ships in Block 2-3; targets are pre-wired)
make migrate                     # alembic upgrade head
make seed                        # python -m app.seeds.run
make fresh                       # drop volumes → rebuild → migrate → seed
make shell-db                    # psql in postgres container
make shell-app                   # bash in app container

# Lint
cd backend && ruff check .
cd backend && ruff format .
```

`Makefile` is the canonical command surface — prefer it over remembering raw `docker compose ...` lines.

## Conventions

- **All API routes live under `/api/*`.** OpenAPI is at `/api/openapi.json`, Swagger at `/api/docs`. The root path is reserved for the SPA in prod.
- **App factory pattern.** `app.main.create_app()` builds the FastAPI app; module-level `app = create_app()` is the uvicorn entrypoint. New routers register in `create_app()` with `prefix="/api"`.
- **Settings via `app.core.config.get_settings()`.** It's `lru_cache`d — don't call it at import time inside hot paths, and don't instantiate `Settings()` directly in tests. `tests/conftest.py` sets env vars *before* importing `app.main` so the cached settings reflect the test env.
- **DB session via `Depends(get_db)`** from `app.db.base`. Never construct `SessionLocal()` ad-hoc inside routes.
- **Tests are smoke tests, not coverage.** ADR-11. New code doesn't need a unit test unless it's on the critical demo path or guards tenant isolation. `pytest -ra -q` is configured in `pyproject.toml`.
- **One commit per logical chunk.** Submission checklist (`docs/PLAN.md §6`) says no `wip` or `fix` cascades. Mention the block number from PLAN.md in the commit subject when relevant.

## What lives where

- `docs/PRD.md` — requirements + FR IDs (`FR-1` through `FR-20`, `NFR-*`). Cross-referenced from `docs/PLAN.md` blocks.
- `docs/HLD.md` — API surface, full DB schema, sequence diagrams, demo script.
- `docs/ARCHITECTURE.md` — tech choices, ADRs, security posture, known gaps.
- `docs/PLAN.md` — build order, milestones, cut order, submission checklist, risk register.
- `backend/app/` — `api/` (auth, transactions, onboarding, reports, dashboard, health), `core/` (config, security, deps), `db/` (base, models), `extraction/` (base, schema, fixture, claude, gemini, factory), `schemas/`, `services/`, `seeds/`. All fully implemented.
- `backend/seeds/extractions/` — 8 fixture extraction JSONs for `FixtureProvider` (matched by file stem on upload).
- `frontend/src/` — `pages/` (all roles), `components/` (layout, ui, upload, transactions), `hooks/` (all API hooks), `store/` (auth), `router/`, `types/`, `lib/` (axios client, queryClient).
- `data/uploads/` — bind-mounted upload directory (gitkept). Seed script writes placeholder files here.

## Gotchas

- **`pip install -e ".[dev]"`** is the install command — the project uses optional dependency groups (`dev`, `ai`). Don't `pip install fastapi sqlalchemy ...` directly.
- **psycopg 3, not psycopg2.** DSNs use `postgresql+psycopg://...` (note the `+psycopg` suffix). Copy from `.env.example`.
- **`make fresh` will drop the Postgres volume.** Safe to run — the seed script is idempotent and rebuilds all demo data automatically.
- **Production Dockerfile (Block 23-25):** needs a multi-stage build — `FROM node:20 AS frontend-build` → `npm run build` → `FROM python:3.12-slim` → copy `dist/` to `backend/app/static/`. FastAPI's `StaticFiles` mount at `/` (non-`/api` paths) serves the SPA. The dev `docker-compose.yml` bind-mounts `./backend:/app` which overrides the container's static files; the prod compose must drop that volume mount and use `COPY` instead.
- **Pre-commit hooks may include a fact-forcing gate** that asks for context before edits/writes — provide the facts inline and retry; don't disable it unless explicitly asked.
- **bcrypt is pinned to 4.0.1** in `pyproject.toml`. `passlib[bcrypt]==1.7.4` is incompatible with bcrypt ≥ 4.1. Don't bump bcrypt without testing `hash_password` and `verify_password` in Docker.
- **`LoginRequest.email` is `str`, not `EmailStr`** — `email-validator` rejects `.local` domains used in seed data. Keep it as `str` with `min_length`/`max_length` constraints.
