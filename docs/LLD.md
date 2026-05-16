# FinBridge — Low-Level Design

Module-level detail for the implementation described in [HLD.md](./HLD.md) and [ARCHITECTURE.md](./ARCHITECTURE.md). This document covers function signatures, internal algorithms, state machines, dependency wiring, and the frontend component tree.

---

## 1. Backend Module Map

```
backend/app/
├── main.py                 create_app() factory; router registration; SPA fallback handler
├── core/
│   ├── config.py           Settings (pydantic-settings); get_settings() lru_cache singleton
│   ├── security.py         hash_password / verify_password; create_access_token / decode_token
│   └── deps.py             current_user, require_role, TenantContext, tenant_scope, get_extraction_provider
├── db/
│   ├── base.py             SQLAlchemy Base; SessionLocal; get_db() generator dependency
│   └── models.py           ORM models: Firm, Company, User, PaymentHead, Transaction, Attachment, Report, AuditLog
├── api/
│   ├── auth.py             POST /auth/login, GET /auth/me
│   ├── onboarding.py       firms, companies, payment-heads, users endpoints
│   ├── transactions.py     upload, manual, list, get, patch, submit, approve, reject, request-info, attachment
│   ├── reports.py          list, upload, file-download
│   ├── dashboard.py        GET /dashboard/summary
│   └── health.py           GET /health
├── schemas/
│   ├── auth.py             LoginRequest, TokenResponse, UserOut
│   ├── transactions.py     TransactionOut, TransactionManualCreate, TransactionPatch
│   ├── onboarding.py       FirmCreate, CompanyCreate, UserCreate, PaymentHeadCreate, …Out schemas
│   └── reports.py          ReportOut
├── services/
│   ├── transactions.py     All transaction business logic (upload_file, create_manual, list, patch, submit, approve, reject, request_info)
│   ├── onboarding.py       firm/company/user/payment-head creation logic
│   ├── reports.py          report upload and download logic
│   └── dashboard.py        dashboard summary aggregation
└── extraction/
    ├── base.py             ExtractionProvider protocol; ExtractionError
    ├── schema.py           ExtractedInvoice, LineItem Pydantic models
    ├── fixture.py          FixtureProvider — SHA-256 + stem lookup
    ├── claude.py           ClaudeProvider — tool-use against claude-sonnet-4-6
    ├── gemini.py           GeminiProvider — responseSchema against gemini-2.5-flash
    └── factory.py          build_provider(settings) → ExtractionProvider
```

---

## 2. Application Startup Sequence

```
uvicorn app.main:app
        │
        ▼
create_app(settings=None)
  ├── get_settings()                          # lru_cache: reads .env once
  ├── FastAPI(..., lifespan=_lifespan)
  ├── app.include_router(health.router,       prefix="/api")
  ├── app.include_router(auth.router,         prefix="/api")
  ├── app.include_router(transactions.router, prefix="/api")
  ├── app.include_router(onboarding.router,   prefix="/api")
  ├── app.include_router(reports.router,      prefix="/api")
  ├── app.include_router(dashboard.router,    prefix="/api")
  └── if static_dir exists:
        mount /assets → StaticFiles
        register 404 exception handler → serve index.html (SPA fallback)

_lifespan(app)  [on startup]
  └── app.state.extraction_provider = build_provider(app.state.settings)
```

`build_provider` reads `settings.EXTRACTION_PROVIDER`:
- `"fixture"` → `FixtureProvider(seeds_dir=settings.FIXTURE_SEEDS_DIR)`
- `"claude"` → `ClaudeProvider(api_key=settings.ANTHROPIC_API_KEY, model=settings.CLAUDE_MODEL)`
- `"gemini"` → `GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)`

The provider is instantiated **once** at startup and stored in `app.state`. Routes retrieve it via `Depends(get_extraction_provider)`, which reads `request.app.state.extraction_provider`.

---

## 3. Settings (`app/core/config.py`)

```python
class Settings(BaseSettings):
    APP_ENV: Literal["development", "test", "production"] = "development"
    DATABASE_URL: str = "postgresql+psycopg://finbridge:finbridge@localhost:5432/finbridge"
    JWT_SECRET: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440          # 24 hours
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    EXTRACTION_PROVIDER: Literal["fixture", "claude", "gemini"] = "fixture"
    FIXTURE_SEEDS_DIR: str = "seeds/extractions"
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
```

**Validator:** `_reject_default_secret_in_production` raises `ValueError` if `APP_ENV == "production"` and `JWT_SECRET` is still the default.

`get_settings()` is `lru_cache(maxsize=1)` — called once, frozen for the process lifetime. Tests override by setting env vars **before** first import of `app.main`.

---

## 4. Security (`app/core/security.py`)

| Function | Inputs | Output | Notes |
|---|---|---|---|
| `hash_password(plain)` | `str` | `str` (bcrypt hash) | passlib CryptContext; bcrypt pinned to 4.0.1 |
| `verify_password(plain, hashed)` | `str, str` | `bool` | passlib constant-time compare |
| `create_access_token(payload)` | `dict` | `str` (JWT) | Adds `iat`, `exp`; signs with `JWT_SECRET` / `JWT_ALGORITHM` |
| `decode_token(token)` | `str` | `dict` (claims) | Raises `ValueError` on `JWTError`; caller converts to 401 |

JWT payload structure:
```json
{
  "sub": "<user_id UUID>",
  "role": "company_user",
  "firm_id": "<uuid|null>",
  "company_id": "<uuid|null>",
  "iat": 1748000000,
  "exp": 1748086400
}
```

---

## 5. Dependency Chain (`app/core/deps.py`)

FastAPI resolves dependencies once per request and deduplicates by function identity (so `get_db` called from both `current_user` and `tenant_scope` returns the same `Session`).

```
get_db()
  └── yields SessionLocal() → closes on exit

current_user(credentials, db)
  ├── credentials = None  →  401 "Not authenticated"
  ├── decode_token(credentials.credentials)
  │     raises ValueError  →  401 "Invalid token"
  ├── claims["sub"] missing or invalid UUID  →  401
  └── db.get(User, uid) is None  →  401 "User not found"
      returns User ORM object

require_role(*roles)                   # factory; returns a dependency function
  └── _check(user=Depends(current_user))
        user.role not in roles  →  403 "Forbidden"
        returns User

tenant_scope(user, db)
  └── returns TenantContext(
            firm_id=user.firm_id,
            company_id=user.company_id,
            role=user.role,
            _db=db,
        )
```

### TenantContext.allowed_companies (lazy, cached per request)

```python
@property
def allowed_companies(self) -> list[uuid.UUID]:
    if self._companies_cache is not None:
        return self._companies_cache
    match self.role:
        case "platform_admin":
            result = []           # handled explicitly by callers
        case "firm_admin" | "accountant":
            result = [row[0] for row in
                      SELECT id FROM companies WHERE firm_id = self.firm_id]
        case "company_user":
            result = [self.company_id] if self.company_id else []
        case _:
            result = []
    self._companies_cache = result
    return result
```

The DB query runs at most once per request; subsequent calls within the same request hit the in-memory cache.

---

## 6. Database Session (`app/db/base.py`)

```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Routes declare `db: Annotated[Session, Depends(get_db)]`. FastAPI manages the generator lifecycle — `db.close()` is called after the response is sent. Transactions are committed explicitly inside service functions (`db.commit()`); the session never auto-commits.

---

## 7. ORM Models (`app/db/models.py`)

All models use SQLAlchemy 2.0 `Mapped` typed columns. Primary keys are `UUID(as_uuid=True)` with `default=uuid.uuid4`. Timestamps use `server_default=func.now()` so the DB clock is authoritative.

### Enum constraints (DB-enforced CHECK constraints)
```python
USER_ROLES         = ("platform_admin", "firm_admin", "accountant", "company_user")
TRANSACTION_TYPES  = ("invoice", "payment", "salary_register", "bank_statement")
TRANSACTION_DIRECTIONS = ("purchase", "sales", "payment_in", "payment_out")
TRANSACTION_STATUSES   = ("draft_ai", "pending_review", "needs_info", "accepted", "rejected")
```

These are rendered as `CHECK (column IN (...))` via `CheckConstraint` in `__table_args__`. Any value outside the tuple causes a DB-level integrity error.

### Key relationships
- `Firm.companies` ↔ `Company.firm` (one-to-many)
- `Transaction.attachments` ↔ `Attachment.transaction` (one-to-many, cascade `all, delete-orphan`)
- `PaymentHead.parent_head_id` → `payment_heads.id` (self-referential tree, nullable root)
- `Transaction.possible_duplicate_of` → `transactions.id` (`SET NULL` on delete)

### Index strategy
```
companies(firm_id)
users(firm_id), users(company_id)
payment_heads(company_id), payment_heads(parent_head_id)
transactions(company_id, status)            — composite; covers queue queries
transactions(company_id, created_at DESC)   — raw SQL in migration (SQLAlchemy can't express DESC ordering portably)
attachments(transaction_id)
reports(company_id)
audit_log(entity_type, entity_id)
```

---

## 8. Transaction Service (`app/services/transactions.py`)

### 8.1 `upload_file` — full algorithm

```
1.  Validate MIME type ∈ {image/jpeg, image/png, image/webp, image/heic, application/pdf}
    → 400 if not in set
2.  Read file bytes; len > MAX_UPLOAD_BYTES → 413
3.  Resolve company_id:
      company_user  → ctx.company_id (from JWT, immutable)
      other roles   → body.company_id; 422 if absent; 403 if not in ctx.allowed_companies
4.  Ensure UPLOAD_DIR exists (mkdir -p)
5.  Sanitise filename: Path(name).name → strip dirs; re.sub unsafe chars → _; cap 200 chars
6.  Write bytes to {UPLOAD_DIR}/{uuid4()}_{safe_name}
7.  Call provider.extract(file_path, mime_type):
      success       → ExtractedInvoice
      ExtractionError → raw_extraction = {"error": str(exc)}; extracted = ExtractedInvoice()
8.  INSERT Transaction(status="draft_ai", raw_extraction, fields populated from extracted)
9.  db.flush() to get txn.id; on DB error → unlink written file (avoid orphan files)
10. INSERT Attachment(transaction_id=txn.id, file_path relative to UPLOAD_DIR, …)
11. INSERT AuditLog(action="transaction.upload")
12. db.commit(); db.refresh(txn)
13. Return (txn, extracted)
```

### 8.2 Transaction status machine

```
                    ┌──────────────────────────────────────┐
                    │                                      │
  upload ──▶  draft_ai ──submit──▶  pending_review ──approve──▶  accepted
                    ▲                      │
               needs_info ◀──request_info──┘
                    │                      │
                    └────────submit─────────
                                           │
                                        reject
                                           │
                                           ▼
                                        rejected
```

Status transition guards — each raises 409 if the precondition is not met:

| Operation | Allowed from | Sets status to |
|---|---|---|
| `submit` | `draft_ai`, `needs_info` | `pending_review` |
| `patch` | `draft_ai`, `pending_review`, `needs_info` | unchanged |
| `approve` | `pending_review` | `accepted` |
| `reject` | `pending_review` | `rejected` |
| `request_info` | `pending_review` | `needs_info` |

### 8.3 Duplicate detection (in `submit_transaction`)

On submit, if both `txn.vendor` and `txn.invoice_no` are non-null:
```sql
SELECT id FROM transactions
WHERE company_id = :cid
  AND vendor = :vendor
  AND invoice_no = :invoice_no
  AND status = 'accepted'
  AND id != :txn_id
LIMIT 1
```
If found, `txn.possible_duplicate_of = dup.id`. The transaction still moves to `pending_review`; the accountant sees a warning in the review UI.

### 8.4 Audit logging (`_audit` helper)

Every mutating service function calls `_audit(db, actor_id, action, entity_id, payload=None)`:
```python
db.add(AuditLog(
    actor_user_id=actor_id,
    action=action,            # e.g. "transaction.approve"
    entity_type="transaction",
    entity_id=entity_id,
    payload=payload,          # optional dict, e.g. {"status": "accepted"}
))
```
The row is added to the same session and committed atomically with the state change.

---

## 9. Extraction Subsystem

### 9.1 `FixtureProvider` lookup algorithm

```python
file_bytes = file_path.read_bytes()
sha256 = hashlib.sha256(file_bytes).hexdigest()

candidates = [
    seeds_dir / f"{sha256}.json",        # exact content hash match
    seeds_dir / f"{file_path.stem}.json" # filename stem match
]
for candidate in candidates:
    if candidate.exists():
        return ExtractedInvoice.model_validate_json(candidate.read_text())

return _generic_mock()   # plausible fallback data, confidence 0.5
```

The SHA-256 path survives renames. The stem path supports seed-script uploads where files are copied under their original names.

### 9.2 `ClaudeProvider` strategy

1. Read file bytes; base64-encode.
2. Build an Anthropic SDK messages request with a `tool` whose `input_schema` is `ExtractedInvoice.model_json_schema()`.
3. `mime_type == "application/pdf"` → `document` block; otherwise → `image` block.
4. Call `claude-sonnet-4-6` with `tool_choice={"type": "tool", "name": "extract_invoice"}` to force structured output.
5. Parse the `tool_use` block → `ExtractedInvoice.model_validate(result)`.
6. On `anthropic.APIError` → raise `ExtractionError(message, retryable=True)`.

### 9.3 `GeminiProvider` strategy

1. Convert file to `Part.from_data(mime_type, data=bytes)`.
2. Call `gemini-2.5-flash` with `generation_config=GenerationConfig(response_mime_type="application/json", response_schema=ExtractedInvoice)`.
3. Parse `.text` → `ExtractedInvoice.model_validate_json(response.text)`.
4. On `google.api_core.exceptions.GoogleAPIError` → raise `ExtractionError`.

### 9.4 `ExtractionError`

```python
class ExtractionError(Exception):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable
```

Caught in `upload_file`. On error: `raw_extraction = {"error": str(exc)}`; transaction is created in `draft_ai` with empty fields; UI shows "AI extraction unavailable — please fill manually."

---

## 10. Auth API (`app/api/auth.py`)

### `POST /api/auth/login`

```
Request:  LoginRequest { email: str (min 1, max 320), password: str }

1. db.query(User).filter(User.email == body.email).first()
   → None → 401 "Invalid credentials"
2. verify_password(body.password, user.password_hash)
   → False → 401 "Invalid credentials"
3. create_access_token({
       "sub": str(user.id),
       "role": user.role,
       "firm_id": str(user.firm_id) or None,
       "company_id": str(user.company_id) or None,
   })
4. Return 200 { access_token, token_type="bearer", user: UserOut }
```

`LoginRequest.email` is `str` (not `EmailStr`) because `.local` TLD domains used in seed data fail `email-validator`'s DNS validation.

### `GET /api/auth/me`

Returns `UserOut` for the authenticated user. No extra DB query — `current_user` already loaded the user row.

---

## 11. Onboarding API (`app/api/onboarding.py`)

### `POST /api/firms` (platform_admin only)
```
1. INSERT Firm(name)
2. INSERT User(email, password_hash=hash(password), role="firm_admin", firm_id=firm.id)
3. db.commit()
→ FirmOut
```
Both rows in one transaction — atomically creates firm and its first admin.

### `POST /api/companies` (firm_admin only)
```
1. INSERT Company(name, business_type, firm_id=ctx.firm_id)
2. Apply payment-head template for business_type (batch INSERT PaymentHead rows)
3. INSERT User(email, password_hash, role="company_user", firm_id, company_id=company.id)
4. db.commit()
→ CompanyOut
```

### Payment-head template application

Templates are hardcoded in `onboarding.py` as `dict[str, list[tuple[str, list[str]]]]`. For each `(head_name, sub_heads)` pair:
```
parent = INSERT PaymentHead(company_id, name=head_name, parent_head_id=None)
db.flush()  # get parent.id
for sub_name in sub_heads:
    INSERT PaymentHead(company_id, name=sub_name, parent_head_id=parent.id)
```

### `GET /api/companies/{id}/payment-heads`

Returns a flat list of `PaymentHeadOut` (id, name, parent_head_id). The frontend reconstructs the two-level tree by grouping on `parent_head_id`.

---

## 12. Reports Service (`app/services/reports.py`)

### Upload (`POST /api/reports`, accountant only)
```
1. Validate MIME ∈ {application/pdf, text/csv, application/vnd.ms-excel,
                    application/vnd.openxmlformats-officedocument.spreadsheetml.sheet}
2. Read bytes; enforce MAX_UPLOAD_BYTES
3. Resolve + authorise company_id via ctx.allowed_companies
4. Write to {UPLOAD_DIR}/{uuid4()}_{safe_name}
5. INSERT Report(company_id, title, file_path, mime_type, original_name, uploaded_by)
6. INSERT AuditLog(action="report.upload")
7. db.commit()
→ ReportOut
```

### Download (`GET /api/reports/{id}/file`)
```
1. db.get(Report, id) → 404 if missing
2. report.company_id not in ctx.allowed_companies → 403
3. Return FileResponse(UPLOAD_DIR / report.file_path,
                       media_type=report.mime_type,
                       filename=report.original_name)
```

---

## 13. Dashboard (`app/services/dashboard.py`)

`GET /api/dashboard/summary` runs three queries scoped to `ctx.allowed_companies`:

1. **Status counts** — `SELECT status, COUNT(*) FROM transactions WHERE company_id IN (...) GROUP BY status`
2. **Top expense heads** — `SELECT ph.name, SUM(t.amount) FROM transactions t JOIN payment_heads ph ... GROUP BY ph.id ORDER BY SUM DESC LIMIT 5`
3. **Recent transactions** — last 10 rows by `created_at DESC`, any status

Response shape:
```json
{
  "counts": { "draft_ai": 2, "pending_review": 3, "needs_info": 1, "accepted": 12, "rejected": 0 },
  "top_heads": [{ "name": "Raw Materials", "total": 245000.00 }, ...],
  "recent": [ ...TransactionOut... ]
}
```

---

## 14. File Handling

### Upload path construction
```python
upload_dir = Path(settings.UPLOAD_DIR)   # /data/uploads
safe_name  = _safe_filename(file.filename)
file_path  = upload_dir / f"{uuid4()}_{safe_name}"
```

`_safe_filename(name)` algorithm:
```
1. Path(name).name              — strip any directory traversal prefix
2. re.sub(r"[^\w.\- ]", "_", name)  — replace unsafe characters
3. name[:200] or "upload"       — cap length; guarantee non-empty
```

`attachments.file_path` stores the path **relative to** `UPLOAD_DIR` (e.g. `a1b2c3_invoice.pdf`). The download endpoint reconstructs the absolute path as `Path(UPLOAD_DIR) / attachment.file_path`.

### Attachment streaming
```python
return FileResponse(
    str(Path(settings.UPLOAD_DIR) / attachment.file_path),
    media_type=attachment.mime_type,
    filename=attachment.original_name,
)
```

---

## 15. SPA Serving (production)

The built React bundle is copied into `backend/app/static/` during the Docker multi-stage build:
```
backend/app/static/
  index.html
  assets/
    index-[hash].js
    index-[hash].css
```

Two registrations in `create_app`:
1. `app.mount("/assets", StaticFiles(directory="static/assets"))` — hashed JS/CSS (browser-cacheable)
2. `StarletteHTTPException` handler: catches 404s on paths that do **not** start with `/api` → serves `static/index.html` → React Router handles client-side navigation

Dynamic routes registered after `create_app()` (e.g. in tests) are never shadowed because the handler fires only on 404, not as a wildcard route registered before the API routes.

---

## 16. Frontend Architecture

### Layer structure

```
src/
├── main.tsx                    React root — QueryClientProvider + RouterProvider
├── router/
│   └── index.tsx               Route tree; RequireRole guard component
├── store/
│   └── auth.ts                 Zustand store: { user, token, login(), logout() }
│                               Persisted to localStorage via zustand/middleware/persist
├── lib/
│   ├── axios.ts                Axios instance; baseURL "/api"; 401 interceptor → logout + /login
│   └── queryClient.ts          TanStack Query client; staleTime 30 000 ms; retry 1
├── hooks/
│   ├── useTransactions.ts      useQuery + useMutation wrappers for all transaction endpoints
│   ├── useOnboarding.ts        firms, companies, payment-heads, users hooks
│   ├── useReports.ts           reports list + upload + download hooks
│   └── useDashboard.ts         dashboard summary hook
├── pages/
│   ├── LoginPage.tsx
│   ├── DashboardPage.tsx
│   ├── platform/
│   │   └── FirmsPage.tsx
│   ├── firm/
│   │   ├── CompaniesPage.tsx
│   │   ├── PaymentHeadsPage.tsx
│   │   └── TeamPage.tsx
│   ├── company/
│   │   ├── UploadPage.tsx              drag-drop → extraction preview → edit form → submit
│   │   ├── TransactionHistoryPage.tsx
│   │   └── ReportsPage.tsx
│   └── accountant/
│       ├── QueuePage.tsx               pending_review list
│       ├── TransactionDetailPage.tsx   side-by-side: file viewer + editable form + action buttons
│       └── ReportsUploadPage.tsx
└── components/
    ├── layout/
    │   └── AppShell.tsx        sidebar nav; role-aware links; logout button
    ├── ui/                     shadcn/ui re-exports (Button, Card, Badge, Input, …)
    ├── upload/
    │   └── FileDropzone.tsx    react-dropzone wrapper; client-side MIME + size validation
    └── transactions/
        ├── TransactionCard.tsx
        ├── ExtractionPreview.tsx   renders ExtractedInvoice fields with confidence badges
        └── StatusBadge.tsx
```

### Auth flow (frontend)

```
LoginPage
  └── POST /api/auth/login
        │ success
        ▼
   authStore.login({ token, user })   [Zustand action]
        ├── writes token + user to store
        └── localStorage via persist middleware
             │
             ▼
   navigate(role-default-route)
```

Every Axios request injects `Authorization: Bearer ${store.token}` via a request interceptor. On a 401 response, the response interceptor calls `authStore.logout()` (clears store + localStorage) and navigates to `/login`, preserving the intended route in `location.state`.

### RequireRole guard

```tsx
function RequireRole({ roles, children }) {
  const user = useAuthStore(s => s.user);
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (!roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return children;
}
```

### TanStack Query conventions

- All `GET` hooks: `useQuery({ queryKey: ["resource", ...filters], queryFn: ... })`
- All mutations: `useMutation({ mutationFn, onSuccess: () => queryClient.invalidateQueries([...]) })`
- Optimistic updates are **not** used — correctness over speed for financial data
- `staleTime: 30_000` ms — queue refetches on window focus; no WebSocket needed for demo loads

---

## 17. Seed Script (`app/seeds/run.py`)

Idempotent via `INSERT … ON CONFLICT DO NOTHING` on natural keys (`users.email`, `firms.name`, `companies(firm_id, name)`).

Seed order (FK dependency-safe):
```
1. INSERT firms       ("Sharma & Co.")
2. INSERT users       platform_admin, firm_admin
3. INSERT companies   Acme Manufacturing (manufacturing), Lumen IT (it)
4. INSERT payment_heads  templates per company (hardcoded tree)
5. INSERT users       2 accountants (firm-scoped), 2 company_users (company-scoped)
6. Copy bill files    to UPLOAD_DIR under their original names
7. INSERT transactions   ~10 rows mixing all statuses + matching attachments
8. INSERT reports     1 MIS PDF pre-attached to Acme Manufacturing
```

Fixture extractions in `seeds/extractions/` are matched by filename stem — bills are copied using their original names so `FixtureProvider`'s stem lookup finds the correct JSON without needing a SHA-256 pre-hash.

---

## 18. Alembic Migration Structure

```
alembic/
├── env.py          imports app.db.base.Base.metadata; reads DATABASE_URL from env
└── versions/
    └── 0001_initial.py   creates all 8 tables + indexes in one migration
```

Tables are created in FK-safe order: `firms → companies → users → payment_heads → transactions → attachments → reports → audit_log`.

The `transactions(company_id, created_at DESC)` composite index is created via `op.execute("CREATE INDEX … DESC")` because SQLAlchemy's `Index` API cannot express column-level `DESC` ordering in a portable way across database backends.

---

## 19. Docker Build (`backend/Dockerfile`)

Multi-stage build:

```dockerfile
# Stage 1: build React SPA
FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build          # outputs dist/

# Stage 2: Python runtime
FROM python:3.12-slim
WORKDIR /app
COPY backend/pyproject.toml backend/README.md ./
RUN pip install -e ".[dev]"
COPY backend/ .
COPY --from=frontend-build /frontend/dist ./app/static

EXPOSE 8000
ENTRYPOINT ["sh", "-c",
  "alembic upgrade head && python -m app.seeds.run && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

The dev `docker-compose.dev.yml` bind-mounts `./backend:/app`, which **shadows** `app/static/` from the Docker layer — intentional, because dev mode uses Vite on port 5173 instead.

The production `docker-compose.yml` has **no** bind-mount on the app container, so the built static files are served.

---

## 20. Test Structure (`backend/tests/`)

Smoke tests only (ADR-11). No coverage targets.

| File | What it covers |
|---|---|
| `test_health.py` | `GET /health` returns 200 |
| `test_auth.py` | login success; wrong password → 401; token claims correct |
| `test_upload.py` | upload with FixtureProvider → draft transaction with extracted fields |
| `test_approve.py` | submit → approve flow; second approve → 409 |
| `test_tenant_isolation.py` | company_user A cannot read company B's transactions (403) |

`conftest.py` sets env vars (`DATABASE_URL`, `EXTRACTION_PROVIDER=fixture`) **before** importing `app.main` so `get_settings()` lru_cache picks up the test values. Each test uses `TestClient(create_app())` with a shared test database that is migrated once per session.

---

## 21. Known Implementation Gaps

| Gap | Location | Impact |
|---|---|---|
| No DB-layer tenant isolation (no RLS) | All service queries | App-layer bypass would leak cross-tenant data |
| No rate limiting | All API routes | Brute-force login and upload spam are possible |
| No pagination | `list_transactions`, `list_reports` | Hard-coded `LIMIT 100`; large datasets will silently truncate |
| Extraction runs inline (synchronous) | `upload_file` | Slow Claude/Gemini calls block the HTTP request thread |
| MIME validation is header-only | `upload_file` | Client-supplied `Content-Type` is trusted; file bytes not inspected |
| Audit log has no API endpoint | `audit_log` table | Data is written but not surfaced to any UI or API consumer |
| JWT has no revocation | Auth | Logout clears client state only; the token remains valid until its 24-hour expiry |

---

## 22. References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — system structure, tech choices, ADRs
- [HLD.md](./HLD.md) — API surface, data model, user flows, extraction contract
- [PRD.md](./PRD.md) — functional requirements (FR-1 through FR-20)
- [PLAN.md](./PLAN.md) — build order, milestones, submission checklist
