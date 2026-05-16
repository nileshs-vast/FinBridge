"""Block 3-5 smoke tests: login + /me + role guard."""
from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import require_role
from app.core.security import hash_password
from app.db.base import Base, get_db
from app.db.models import Company, Firm, User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def auth_client(db_session: Session) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


@pytest.fixture()
def seed_users(db_session: Session):
    firm = Firm(name="Test Firm")
    db_session.add(firm)
    db_session.flush()

    company_a = Company(firm_id=firm.id, name="Company A", business_type="it")
    db_session.add(company_a)
    db_session.flush()

    admin = User(
        email="admin@test.local",
        password_hash=hash_password("secret123"),
        role="firm_admin",
        firm_id=firm.id,
    )
    user_a = User(
        email="user_a@test.local",
        password_hash=hash_password("secret123"),
        role="company_user",
        firm_id=firm.id,
        company_id=company_a.id,
    )
    db_session.add_all([admin, user_a])
    db_session.flush()
    return {"admin": admin, "user_a": user_a, "company_a": company_a}


def test_login_ok(auth_client, seed_users):
    resp = auth_client.post(
        "/api/auth/login", json={"email": "admin@test.local", "password": "secret123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["role"] == "firm_admin"


def test_login_wrong_password(auth_client, seed_users):
    resp = auth_client.post(
        "/api/auth/login", json={"email": "admin@test.local", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_unknown_email(auth_client, seed_users):
    resp = auth_client.post(
        "/api/auth/login", json={"email": "nobody@test.local", "password": "x"}
    )
    assert resp.status_code == 401


def test_me_with_valid_token(auth_client, seed_users):
    token = auth_client.post(
        "/api/auth/login", json={"email": "admin@test.local", "password": "secret123"}
    ).json()["access_token"]
    resp = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.local"


def test_me_no_token(auth_client):
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_invalid_token(auth_client):
    resp = auth_client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_cross_tenant_isolation(db_session: Session):
    """firm_admin from Firm A must not reach data owned by Firm B (CLAUDE.md requirement)."""
    from app.core.deps import tenant_scope
    from app.main import create_app

    firm_a = Firm(name="Firm A")
    firm_b = Firm(name="Firm B")
    db_session.add_all([firm_a, firm_b])
    db_session.flush()

    co_b = Company(firm_id=firm_b.id, name="Company B", business_type="services")
    db_session.add(co_b)
    db_session.flush()

    admin_a = User(
        email="admin_a@test.local",
        password_hash=hash_password("secret123"),
        role="firm_admin",
        firm_id=firm_a.id,
    )
    db_session.add(admin_a)
    db_session.flush()

    scoped_route = APIRouter()

    @scoped_route.get("/test-scoped")
    def scoped(ctx=Depends(tenant_scope)):
        return {"companies": [str(c) for c in ctx.allowed_companies]}

    app2 = create_app()
    app2.dependency_overrides[get_db] = lambda: db_session
    app2.include_router(scoped_route, prefix="/api")
    client2 = TestClient(app2)

    token = client2.post(
        "/api/auth/login", json={"email": "admin_a@test.local", "password": "secret123"}
    ).json()["access_token"]

    resp = client2.get("/api/test-scoped", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    # Firm A has no companies — Firm B's company must NOT appear
    assert str(co_b.id) not in resp.json()["companies"]


def test_role_guard_rejects_wrong_role(auth_client, seed_users, db_session):
    """company_user token must get 403 on a firm_admin-only route."""
    from app.main import create_app

    restricted = APIRouter()

    @restricted.get("/test-firm-only")
    def firm_only(_=Depends(require_role("firm_admin"))):
        return {"ok": True}

    app2 = create_app()
    app2.dependency_overrides[get_db] = lambda: db_session
    app2.include_router(restricted, prefix="/api")
    client2 = TestClient(app2)

    company_token = client2.post(
        "/api/auth/login", json={"email": "user_a@test.local", "password": "secret123"}
    ).json()["access_token"]

    resp = client2.get("/api/test-firm-only", headers={"Authorization": f"Bearer {company_token}"})
    assert resp.status_code == 403
