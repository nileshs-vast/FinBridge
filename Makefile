.PHONY: help up dev down build logs ps shell-app shell-db migrate seed fresh test fmt lint backend-install frontend-install dev-backend dev-frontend

help:
	@echo "FinBridge — common tasks"
	@echo ""
	@echo "  make up              docker compose up --build  (production: SPA served by FastAPI)"
	@echo "  make dev             hot-reload dev mode (source bind-mount + --reload)"
	@echo "  make down            docker compose down"
	@echo "  make logs            tail app logs"
	@echo "  make ps              show running containers"
	@echo "  make shell-app       exec bash in the app container"
	@echo "  make shell-db        psql in the postgres container"
	@echo "  make migrate         alembic upgrade head (inside app)"
	@echo "  make seed            run seed script (inside app)"
	@echo "  make fresh           drop volumes, rebuild, migrate, seed"
	@echo "  make test            pytest (inside app)"
	@echo "  make backend-install pip install backend deps locally"
	@echo "  make frontend-install npm install frontend deps locally"
	@echo "  make dev-backend     run uvicorn locally (needs local Postgres)"
	@echo "  make dev-frontend    run vite dev server"

up:
	docker compose up --build

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f app

ps:
	docker compose ps

shell-app:
	docker compose exec app bash

shell-db:
	docker compose exec postgres psql -U $${POSTGRES_USER:-finbridge} -d $${POSTGRES_DB:-finbridge}

migrate:
	docker compose exec app alembic upgrade head

seed:
	docker compose exec app python -m app.seeds.run

fresh:
	docker compose down -v
	docker compose up --build -d
	@echo "waiting for app to be ready..."
	@sleep 5
	docker compose exec app alembic upgrade head
	docker compose exec app python -m app.seeds.run

test:
	docker compose exec app pytest

backend-install:
	cd backend && pip install -e ".[dev]"

frontend-install:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev
