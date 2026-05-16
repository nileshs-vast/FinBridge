"""Smoke test: company_user can upload a file and receive a draft_ai extraction."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
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
def upload_client(db_session: Session) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def seed_upload_users(db_session: Session):
    firm = Firm(name="Upload Test Firm")
    db_session.add(firm)
    db_session.flush()

    company = Company(firm_id=firm.id, name="Upload Test Co", business_type="it")
    db_session.add(company)
    db_session.flush()

    company_user = User(
        email="uploader@uploadtest.local",
        password_hash=hash_password("testpass123"),
        role="company_user",
        firm_id=firm.id,
        company_id=company.id,
    )
    db_session.add(company_user)
    db_session.flush()
    return {"company_user": company_user, "company": company, "firm": firm}


def test_upload_returns_draft_ai(upload_client, seed_upload_users, tmp_path):
    """A company_user uploading a file should get a draft_ai transaction back."""
    # Login to get token
    login_resp = upload_client.post(
        "/api/auth/login",
        json={"email": "uploader@uploadtest.local", "password": "testpass123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # Upload a minimal fake PDF (fixture provider falls back to generic mock for unknown filenames)
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
    resp = upload_client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"transaction_type": "invoice", "direction": "purchase"},
        files={"file": ("test_invoice.pdf", fake_pdf, "application/pdf")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "transaction" in data
    txn = data["transaction"]
    assert txn["id"] is not None
    assert txn["status"] == "draft_ai"


def test_upload_requires_auth(upload_client):
    """Uploading without a token should return 401."""
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
    resp = upload_client.post(
        "/api/transactions/upload",
        data={"transaction_type": "invoice"},
        files={"file": ("test.pdf", fake_pdf, "application/pdf")},
    )
    assert resp.status_code == 401
