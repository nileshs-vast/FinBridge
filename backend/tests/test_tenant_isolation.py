"""Smoke test: cross-tenant transaction isolation — company B cannot access company A's transactions."""
from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import Base, get_db
from app.db.models import Company, Firm, Transaction, User


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
def isolation_client(db_session: Session) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


@pytest.fixture()
def seed_two_companies(db_session: Session):
    """Seed two companies under the same firm, each with a company_user and a transaction."""
    firm = Firm(name="Isolation Test Firm")
    db_session.add(firm)
    db_session.flush()

    company_a = Company(firm_id=firm.id, name="Company Alpha", business_type="it")
    company_b = Company(firm_id=firm.id, name="Company Beta", business_type="manufacturing")
    db_session.add_all([company_a, company_b])
    db_session.flush()

    user_a = User(
        email="user_a@isolation.local",
        password_hash=hash_password("testpass123"),
        role="company_user",
        firm_id=firm.id,
        company_id=company_a.id,
    )
    user_b = User(
        email="user_b@isolation.local",
        password_hash=hash_password("testpass123"),
        role="company_user",
        firm_id=firm.id,
        company_id=company_b.id,
    )
    db_session.add_all([user_a, user_b])
    db_session.flush()

    # Transaction belonging to company A
    txn_a = Transaction(
        company_id=company_a.id,
        transaction_type="invoice",
        direction="purchase",
        vendor="Alpha Vendor",
        invoice_no="ALPHA/001",
        amount=Decimal("99000.00"),
        currency="INR",
        status="pending_review",
        uploaded_by=user_a.id,
    )
    db_session.add(txn_a)
    db_session.flush()

    return {
        "firm": firm,
        "company_a": company_a,
        "company_b": company_b,
        "user_a": user_a,
        "user_b": user_b,
        "txn_a": txn_a,
    }


def test_company_b_cannot_read_company_a_transaction(isolation_client, seed_two_companies):
    """User from company B should get 404 when fetching company A's transaction by ID."""
    txn_a = seed_two_companies["txn_a"]

    # Login as user A and confirm the transaction is visible
    token_a = isolation_client.post(
        "/api/auth/login",
        json={"email": "user_a@isolation.local", "password": "testpass123"},
    ).json()["access_token"]

    resp_a = isolation_client.get(
        f"/api/transactions/{txn_a.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.status_code == 200
    assert resp_a.json()["id"] == str(txn_a.id)

    # Login as user B and attempt to fetch company A's transaction
    token_b = isolation_client.post(
        "/api/auth/login",
        json={"email": "user_b@isolation.local", "password": "testpass123"},
    ).json()["access_token"]

    resp_b = isolation_client.get(
        f"/api/transactions/{txn_a.id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    # Must be 404 (not found within tenant scope) or 403 (forbidden) — never 200
    assert resp_b.status_code in (404, 403)


def test_company_b_list_does_not_include_company_a_transactions(isolation_client, seed_two_companies):
    """User B's transaction list must not contain transactions owned by company A."""
    txn_a = seed_two_companies["txn_a"]

    token_b = isolation_client.post(
        "/api/auth/login",
        json={"email": "user_b@isolation.local", "password": "testpass123"},
    ).json()["access_token"]

    resp = isolation_client.get(
        "/api/transactions",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()]
    assert str(txn_a.id) not in ids
