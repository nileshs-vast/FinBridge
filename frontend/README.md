# Frontend (placeholder)

The full Vite + React + Tailwind + shadcn scaffold lands in **Block 10.5–13.5** of [docs/PLAN.md](../docs/PLAN.md). This file commits the **dev-proxy plan** so the backend work in Blocks 2–10 can run independently against `http://localhost:8000`.

## Dev-proxy plan

Production: FastAPI serves the built SPA from `backend/app/static/` — same origin, no CORS, single port `8000` (see [ARCHITECTURE.md §9](../docs/ARCHITECTURE.md#9-deployment)).

Dev mode: Vite on `5173`, FastAPI on `8000`. Vite proxies `/api/*` to FastAPI so frontend code can call `/api/...` paths verbatim in both environments — no env-driven base URL switch.

### Target `vite.config.ts`

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "../backend/app/static",
    emptyOutDir: true,
  },
});
```

### Workflow

- `make dev-backend` → uvicorn on 8000
- `make dev-frontend` → vite on 5173, proxies `/api` → 8000
- `make up` (prod-ish) → docker compose; FastAPI serves both API and the prebuilt SPA on 8000

### Why this shape

- Same `/api` prefix in dev and prod → no axios baseURL switching.
- Vite writes its production bundle directly into the FastAPI static dir, so the backend Docker image picks it up in one multi-stage copy step (planned for Block 23–25 per PLAN.md).
