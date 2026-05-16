# FinBridge — Implementation Plan

48-hour build schedule. References [PRD.md](./PRD.md) FR-IDs and [HLD.md](./HLD.md) flows. Demo-first ordering — the upload→extract→review path comes online by end of Day 1, polish happens Day 2.

---

## 0. Build status (as of 2026-05-16, Day 2 — COMPLETE)

| Block | Status | Notes |
|---|---|---|
| 0–1 | ✓ DONE | Fixture extractions in `backend/seeds/extractions/` |
| 1–2.5 | ✓ DONE | Scaffold, docker-compose, Makefile, FastAPI app factory, pytest |
| 2–3 | ✓ DONE | Alembic + all 8 ORM models |
| 3–5 | ✓ DONE | JWT auth, bcrypt, deps, `/api/auth/login`, `/api/auth/me` |
| 5–7 | ✓ DONE | ExtractionProvider + FixtureProvider + ClaudeProvider + GeminiProvider |
| 7–8 | ✓ DONE | All transactions API endpoints |
| 8–9 | ✓ DONE | All onboarding API endpoints |
| 9–10 | ✓ DONE | Reports API + dashboard summary |
| 10.5–13.5 | ✓ DONE | Frontend scaffold: Vite + Tailwind + shadcn + TanStack Query + Zustand + router + login |
| 12–14 | ✓ DONE | Company user upload + extraction preview + submit |
| 14–16 | ✓ DONE | Accountant queue + transaction detail + approve/reject |
| 16–17 | ✓ DONE | Seed script (`make seed`); 6 users, 2 companies, 10 transactions, 1 MIS report |
| 17–18 | ✓ DONE | FirmsPage, CompaniesPage, TeamPage, PaymentHeadsPage |
| 18–19 | ✓ DONE | ReportsPage, ReportsUploadPage |
| 19–20 | ✓ DONE | ManualTransactionPage (payment / salary_register) |
| 20–21 | ✓ DONE | DashboardPage (counts + recent table + top-heads chart) |
| 21–22 | ✓ DONE | UX polish: navigation, loading/empty states, toasts, form validation |
| 23–25 | ✓ DONE | Docker multi-stage build; FastAPI serves React SPA on port 8000 via 404 exception handler |
| 25–26 | ✓ DONE | Smoke tests: 16/16 passing — auth, upload, approve, cross-tenant isolation |
| 26–27 | ✓ DONE | README with one-command setup, credentials table, env vars, troubleshooting |
| 27–28.5 | ✓ DONE | Presentation deck — `docs/presentation.html` (7 slides, incl. Claude Code dev experience) |
| 28.5–29 | ✓ DONE | Demo video script — `docs/demo_script.md` (~3 min timestamped) |
| 29–30 | ✓ DONE | `make fresh` clean build verified; `make test` 16/16 green |

---

## 1. Milestones

| Milestone | Hour | Definition of done |
|---|---|---|
| **M0 — De-risk** | 1 | One real PDF + one phone-photo image extracted via a curl-style Python script to Claude/Gemini/fixture path; structured JSON returned. |
| **M1 — Skeleton up** | 4 | docker compose up brings Postgres + FastAPI + an empty React shell; alembic creates all tables; auth login returns a JWT. |
| **M2 — AI loop alive** | 10 | Logged-in company user uploads a bill, extraction runs, draft persisted, returned to UI. |
| **M3 — End-to-end ugly** | 14 | Full demo path works: upload → extract → preview → submit → review → approve → appears in history. UI is unstyled but functional. |
| **M4 — Polished** | 22 | Tailwind/shadcn applied, layout shell, loading/empty/toast states, side-by-side review screen. |
| **M5 — Submission ready** | 30 | Seed data, demo video, deck, README, fresh `docker compose up` runs cleanly. |

---

## 2. Day 1 (16h target, 12h focused work)

| Block | Tasks | FR | Est |
|---|---|---|---|
| 0–1 | M0 smoke test: hit Claude/Gemini with one PDF + one image; commit extraction JSON fixtures | FR-8 | 60m |
| 1–2.5 | Repo scaffold, docker-compose, `.env.example`, Makefile, Postgres healthcheck, FastAPI app factory + SQLAlchemy session + pydantic-settings + backend Dockerfile, pytest scaffolding, Vite dev proxy plan | FR-20 | 90m |
| 2–3 | Alembic init + first migration: firms, companies, users, payment_heads, transactions, attachments, reports, audit_log | — | 60m |
| 3–5 | Auth: bcrypt, JWT issue/verify, `current_user` dep, `require_role`, `tenant_scope` | FR-1, FR-18 | 120m |
| 5–7 | Extraction subsystem: `ExtractionProvider` protocol + `FixtureProvider` + `ClaudeProvider` + `GeminiProvider` + factory | FR-8 | 120m |
| 7–8 | Transactions API: upload, manual, list, get, patch, submit, approve, reject + audit hooks | FR-7–FR-13, FR-16 | 60m |
| 8–9 | Onboarding API: firms, companies (with template), payment-heads, users | FR-2–FR-6 | 60m |
| 9–10 | Reports API + dashboard summary | FR-14, FR-15, FR-17 | 60m |
| 10.5–13.5 | Frontend scaffold: Vite + Tailwind + shadcn init + base components + TanStack Query provider + router + Zustand auth store with persist + axios client with 401 interceptor + protected-route wrapper + layout shell + login page | FR-1 | 180m |
| 12–14 | Company user upload page + extraction preview + edit form + submit | FR-7, FR-9 | 120m |
| 14–16 | Accountant queue + transaction detail (file viewer + form) + approve/reject | FR-11, FR-12, FR-13 | 120m |

**End-of-Day-1 gate (M3):** demo path runs end-to-end in dev mode. If not green, cut Day 2 hard.

---

## 3. Day 2 (12h target, 10h focused work)

| Block | Tasks | FR | Est |
|---|---|---|---|
| 16–17 | Seed script: firms, companies, payment heads, users, demo bills + matched extractions, pre-staged transactions, one MIS report | FR-19 | 60m |
| 17–18 | Platform admin "create firm" screen + firm admin "create company + add accountant" screens | FR-2, FR-3, FR-6 | 60m |
| 18–19 | Reports UI: accountant upload + company list/download | FR-14, FR-15 | 60m |
| 19–20 | Manual transaction entry UI (payment / salary register) | FR-10 | 60m |
| 20–21 | Dashboard page: counts cards + recent table + top-heads bar chart | FR-17 | 60m |
| 21–22 | UX polish pass: navigation refinements, loading states, empty states, toasts, form validation, error banners (layout shell already shipped in Day-1 Block 10.5–13.5) | NFR-9 | 60m |
| 23–25 | Docker production build: multi-stage frontend → backend serves static; entrypoint runs `alembic upgrade head` + seed; verify single-port boot | FR-20 | 120m |
| 25–26 | Smoke tests: auth, upload, approve, cross-tenant 403 | NFR-7 | 60m |
| 26–27 | README: setup, demo credentials, env vars, troubleshooting, screenshots | NFR-10 | 60m |
| 27–28.5 | Presentation deck (5–8 slides): problem, approach, architecture, AI demo, roadmap | — | 90m |
| 28.5–29 | Demo video recording (one take, ~3 min) | — | 30m |
| 29–30 | End-to-end dry run × 2, fix obvious bugs, final `make fresh` verification | — | 60m |

---

## 4. Dependency graph (critical path)

```
M0 (smoke) ──▶ Auth ──▶ Tenant scope ──▶ Transactions API ──▶ Upload page ──▶ Review queue ──▶ DEMO
                  │           │
                  ▼           ▼
              Onboarding   Extraction provider (parallel after M0)
                  │
                  ▼
              Reports + Dashboard (Day 2)
```

Auth + tenant scope is the single biggest serial dependency. Build it once, well; everything else flows from it.

---

## 5. Cut order if behind

If at hour 14 the M3 gate is missed, cut in this order:

1. **Dashboard** (FR-17) — drop entirely; mention "coming soon" on a placeholder.
2. **Manual transaction entry** (FR-10) — accept that all transactions are invoice-via-AI for the demo; document as known scope reduction.
3. **Audit log writes inside non-transaction services** — keep writes on transaction approve/reject only.
4. **Platform admin UI** (FR-2 UI) — keep the API, demo the create-firm flow via the API tab in the deck.
5. **Reports UI** (FR-15) — keep backend, demo via API.

**Never cut:** FR-1 (auth), FR-7–FR-9 (upload + extraction + preview), FR-11–FR-13 (review queue + approve), FR-18 (tenant isolation), FR-19 (seed), FR-20 (Docker).

---

## 6. Submission checklist

- [ ] GitHub repo public, clean commits (one per logical chunk; no `wip` or `fix` cascades)
- [ ] `README.md` with one-command setup + seeded credentials table + screenshots
- [ ] `.env.example` complete; `.env` gitignored
- [ ] `docker compose up --build` works from a fresh clone (verified once)
- [ ] `make fresh` reseeds the database cleanly
- [ ] All five docs present in `/docs`: ARCHITECTURE, HLD, PRD, PLAN, LLD
- [ ] Presentation deck (5–8 slides) committed under `/docs/presentation.pdf`
- [ ] Demo video (~3 min) linked in README (YouTube unlisted or committed if small)
- [ ] At least 8 demo bills + matching fixture extractions in `seeds/`
- [ ] Smoke tests pass (`pytest backend/tests` green)
- [ ] One sentence in README listing intentional scope cuts (honest)

---

## 7. Risk register

| Risk | Detect | Mitigate |
|---|---|---|
| M0 fails (extraction broken on a sample) | Hour 1 | Fall back to fixture-only for demo; document. |
| Auth bug leaks tenant data | M3 gate / smoke test | Single `tenant_scope` dep; one cross-tenant 403 test. |
| Docker prod build fails late | Hour 23 attempt | Start prod build at hour 23 not hour 28; fall back to dev mode if needed. |
| Time slippage > 2h on any block | Each milestone | Trigger cut order §5 immediately; do not "push through". |
| Demo machine network outage during live demo | Demo day | Record fallback video at hour 29; load offline. |

---

## 8. Demo-day prep (after M5)

- Browser bookmarked to `http://localhost:8000` with login as each role pinned in tabs.
- Demo dataset reset via `make fresh` immediately before recording.
- Backup video stored locally and on cloud.
- Slide deck on the same machine as the running demo.

---

## 9. References

- [PRD.md](./PRD.md) — requirements + FR IDs referenced here
- [HLD.md](./HLD.md) — flows + API surface
- [LLD.md](./LLD.md) — module-level design (what gets built per block above)
- [ARCHITECTURE.md](./ARCHITECTURE.md) — tech choices
