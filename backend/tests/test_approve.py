"""Smoke test: accountant can approve a pending_review transaction."""
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
def approve_client(db_session: Session) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)


@pytest.fixture()
def seed_approve_data(db_session: Session):
    firm = Firm(name="Approve Test Firm")
    db_session.add(firm)
    db_session.flush()

    company = Company(firm_id=firm.id, name="Approve Test Co", business_type="manufacturing")
    db_session.add(company)
    db_session.flush()

    company_user = User(
        email="uploader@approvetest.local",
        password_hash=hash_password("testpass123"),
        role="company_user",
        firm_id=firm.id,
        company_id=company.id,
    )
    accountant = User(
        email="accountant@approvetest.local",
        password_hash=hash_password("testpass123"),
        role="accountant",
        firm_id=firm.id,
        company_id=None,
    )
    db_session.add_all([company_user, accountant])
    db_session.flush()

    # Create a pending_review transaction directly
    txn = Transaction(
        company_id=company.id,
        transaction_type="invoice",
        direction="purchase",
        vendor="Test Vendor Ltd",
        invoice_no="TEST/2024/001",
        amount=Decimal("50000.00"),
        currency="INR",
        status="pending_review",
        uploaded_by=company_user.id,
    )
    db_session.add(txn)
    db_session.flush()

    return {
        "firm": firm,
        "company": company,
        "company_user": company_user,
        "accountant": accountant,
        "txn": txn,
    }


def test_accountant_can_approve_pending_transaction(approve_client, seed_approve_data):
    """An accountant should be able to approve a pending_review transaction."""
    txn = seed_approve_data["txn"]

    # Login as accountant
    login_resp = approve_client.post(
        "/api/auth/login",
        json={"email": "accountant@approvetest.local", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Verify the transaction is visible to the accountant
    list_resp = approve_client.get(
        "/api/transactions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    txn_list = list_resp.json()
    pending = [t for t in txn_list if t["status"] == "pending_review"]
    assert len(pending) >= 1

    # Approve the specific transaction
    approve_resp = approve_client.post(
        f"/api/transactions/{txn.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert approve_resp.status_code == 200
    result = approve_resp.json()
    assert result["status"] == "accepted"
    assert result["id"] == str(txn.id)


def test_company_user_cannot_approve(approve_client, seed_approve_data):
    """A company_user should get 403 when attempting to approve a transaction."""
    txn = seed_approve_data["txn"]

    login_resp = approve_client.post(
        "/api/auth/login",
        json={"email": "uploader@approvetest.local", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    resp = approve_client.post(
        f"/api/transactions/{txn.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
