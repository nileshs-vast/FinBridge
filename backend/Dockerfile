# Stage 1 — Build React frontend
FROM node:20-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# vite outDir is '../backend/app/static' → resolves to /backend/app/static
RUN npm run build

# Stage 2 — Python runtime
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/ .
RUN pip install --upgrade pip \
    && pip install -e ".[dev,ai]"

# Copy built React SPA into the location FastAPI's StaticFiles mount expects
COPY --from=frontend-build /backend/app/static ./app/static

RUN mkdir -p /data/uploads

EXPOSE 8000

# Migrate DB, seed demo data, then start server
CMD ["sh", "-c", "alembic upgrade head && python -m app.seeds.run && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
