"""
E2E test: all 10 sample PDFs through the full invoice approval workflow.

Workflow under test:
  company_user  → POST /upload            → status: draft_ai
  company_user  → POST /{id}/submit       → status: pending_review
  accountant    → GET  /transactions      → sees pending transaction
  accountant    → POST /{id}/approve      → status: accepted
  accountant    → POST /{id}/reject       → status: rejected  (alternate path)
  accountant    → POST /{id}/request-info → status: needs_info (alternate path)

Each PDF filename maps to a fixture JSON in seeds/extractions/{stem}.json via
FixtureProvider, so every upload returns deterministic extracted data that we
can assert on.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_extraction_provider
from app.core.security import hash_password
from app.db.base import Base, get_db
from app.db.models import Company, Firm, User
from app.extraction.fixture import FixtureProvider

# Absolute path so the fixture provider works regardless of CWD
_SEEDS_DIR = Path(__file__).parent.parent / "seeds" / "extractions"

# ---------------------------------------------------------------------------
# Fixtures that define expected extraction values for each PDF file stem.
# These match the vendor/total fields in seeds/extractions/*.json.
# ---------------------------------------------------------------------------

INVOICE_CASES = [
    # (pdf_stem, expected_vendor_substring, expected_total)
    ("bajaj_electricals_invoice",  "Bajaj Electricals",                    47200.0),
    ("bel_electricity_invoice",    "Bharat Electricals",                  118000.0),
    ("dhl_logistics_invoice",      "DHL Logistics",                        59000.0),
    ("larsen_toubro_invoice",      "Larsen",                              236000.0),
    ("mahindra_logistics_invoice", "Mahindra Logistics",                   84100.0),
    ("sail_steel_invoice",         "SAIL",                                325000.0),
    ("salary_register_apr2024",    "Acme Manufacturing",                 1250000.0),
    ("tata_steel_invoice",         "Tata Steel",                          495600.0),
    ("ultratech_cement_invoice",   "Ultratech Cement",                    141600.0),
    ("wipro_infra_invoice",        "Wipro Infrastructure",                 92000.0),
]

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_invoices"


# ---------------------------------------------------------------------------
# Shared DB / client setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def engine():
    eng = create_engine(get_settings().DATABASE_URL, pool_pre_ping=True, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    txn = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    txn.rollback()
    connection.close()


@pytest.fixture()
def e2e_client(db_session: Session) -> TestClient:
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    # Force fixture provider so tests are deterministic regardless of .env EXTRACTION_PROVIDER
    _fixture_provider = FixtureProvider(seeds_dir=str(_SEEDS_DIR))
    app.dependency_overrides[get_extraction_provider] = lambda: _fixture_provider
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def e2e_users(db_session: Session) -> dict:
    """Create a firm, company, company_user, and accountant for E2E tests."""
    firm = Firm(name="E2E Test Firm")
    db_session.add(firm)
    db_session.flush()

    company = Company(firm_id=firm.id, name="E2E Test Co", business_type="manufacturing")
    db_session.add(company)
    db_session.flush()

    company_user = User(
        email="uploader@e2etest.local",
        password_hash=hash_password("testpass123"),
        role="company_user",
        firm_id=firm.id,
        company_id=company.id,
    )
    accountant = User(
        email="accountant@e2etest.local",
        password_hash=hash_password("testpass123"),
        role="accountant",
        firm_id=firm.id,
        company_id=None,
    )
    db_session.add_all([company_user, accountant])
    db_session.flush()

    return {
        "firm": firm,
        "company": company,
        "company_user": company_user,
        "accountant": accountant,
    }


def _login(client: TestClient, email: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]


def _pdf_bytes(stem: str) -> tuple[bytes, str]:
    """Return (file_bytes, filename) — real PDF if present, else a minimal stub."""
    path = SAMPLE_DIR / f"{stem}.pdf"
    if path.exists():
        return path.read_bytes(), f"{stem}.pdf"
    # Stub: fixture provider still matches by original_stem, so the stub works
    return b"%PDF-1.4 stub", f"{stem}.pdf"


# ---------------------------------------------------------------------------
# Step-by-step helpers that return the transaction data at each stage
# ---------------------------------------------------------------------------

def _step_upload(client: TestClient, token: str, stem: str, txn_type: str = "invoice") -> dict:
    """
    Input:  PDF file (real or stub), transaction_type, auth token
    Output: TransactionUploadResponse → transaction{id, status=draft_ai}
            + extracted{vendor, total, line_items}
    """
    file_bytes, filename = _pdf_bytes(stem)
    resp = client.post(
        "/api/transactions/upload",
        headers={"Authorization": f"Bearer {token}"},
        data={"transaction_type": txn_type, "direction": "purchase"},
        files={"file": (filename, io.BytesIO(file_bytes), "application/pdf")},
    )
    assert resp.status_code == 200, f"Upload failed for {stem}: {resp.text}"
    data = resp.json()
    assert "transaction" in data
    assert "extracted" in data
    txn = data["transaction"]
    assert txn["status"] == "draft_ai", f"Expected draft_ai after upload, got {txn['status']}"
    assert txn["id"] is not None
    return data


def _step_submit(client: TestClient, token: str, txn_id: str) -> dict:
    """
    Input:  txn_id in draft_ai (or needs_info) status, company_user token
    Output: transaction{status=pending_review}
    """
    resp = client.post(
        f"/api/transactions/{txn_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Submit failed: {resp.text}"
    txn = resp.json()
    assert txn["status"] == "pending_review", (
        f"Expected pending_review after submit, got {txn['status']}"
    )
    return txn


def _step_list_pending(client: TestClient, token: str, txn_id: str) -> dict:
    """
    Input:  accountant token
    Output: list contains the submitted transaction in pending_review state
    """
    resp = client.get(
        "/api/transactions",
        headers={"Authorization": f"Bearer {token}"},
        params={"status": "pending_review"},
    )
    assert resp.status_code == 200, f"List failed: {resp.text}"
    items = resp.json()
    ids = [t["id"] for t in items]
    assert txn_id in ids, f"Transaction {txn_id} not visible in pending queue"
    match = next(t for t in items if t["id"] == txn_id)
    assert match["status"] == "pending_review"
    return match


def _step_approve(client: TestClient, token: str, txn_id: str) -> dict:
    """
    Input:  txn_id in pending_review, accountant token
    Output: transaction{status=accepted}
    """
    resp = client.post(
        f"/api/transactions/{txn_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Approve failed: {resp.text}"
    txn = resp.json()
    assert txn["status"] == "accepted", f"Expected accepted after approve, got {txn['status']}"
    return txn


def _step_reject(client: TestClient, token: str, txn_id: str, reason: str) -> dict:
    """
    Input:  txn_id in pending_review, accountant token, rejection reason
    Output: transaction{status=rejected}
    """
    resp = client.post(
        f"/api/transactions/{txn_id}/reject",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": reason},
    )
    assert resp.status_code == 200, f"Reject failed: {resp.text}"
    txn = resp.json()
    assert txn["status"] == "rejected", f"Expected rejected, got {txn['status']}"
    return txn


def _step_request_info(client: TestClient, token: str, txn_id: str, reason: str) -> dict:
    """
    Input:  txn_id in pending_review, accountant token, info request reason
    Output: transaction{status=needs_info}
    """
    resp = client.post(
        f"/api/transactions/{txn_id}/request-info",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": reason},
    )
    assert resp.status_code == 200, f"Request-info failed: {resp.text}"
    txn = resp.json()
    assert txn["status"] == "needs_info", f"Expected needs_info, got {txn['status']}"
    return txn


# ---------------------------------------------------------------------------
# Main E2E tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("stem,vendor_substr,expected_total", INVOICE_CASES)
def test_full_approve_workflow(stem, vendor_substr, expected_total, e2e_client, e2e_users):
    """
    Happy path for every sample PDF:
      upload → draft_ai → submit → pending_review → approve → accepted

    Verifies:
    - Correct fixture data is matched by filename (vendor substring + total)
    - Each status transition is enforced in the right order
    - Accountant can see the transaction in the pending queue
    - Approve sets status to accepted
    """
    uploader_token = _login(e2e_client, "uploader@e2etest.local")
    accountant_token = _login(e2e_client, "accountant@e2etest.local")

    # Step 1: Upload
    txn_type = "salary_register" if "salary" in stem else "invoice"
    upload_data = _step_upload(e2e_client, uploader_token, stem, txn_type)
    txn = upload_data["transaction"]
    extracted = upload_data["extracted"]

    # Assert extraction matched the correct fixture
    assert vendor_substr.lower() in (extracted.get("vendor") or "").lower(), (
        f"[{stem}] Expected vendor to contain '{vendor_substr}', got '{extracted.get('vendor')}'"
    )
    assert extracted.get("total") == pytest.approx(expected_total, rel=0.01), (
        f"[{stem}] Expected total {expected_total}, got {extracted.get('total')}"
    )
    assert isinstance(extracted.get("line_items"), list)
    assert len(extracted["line_items"]) >= 1

    txn_id = txn["id"]

    # Step 2: Submit (company_user sends to review queue)
    _step_submit(e2e_client, uploader_token, txn_id)

    # Step 3: Accountant sees it in pending queue
    _step_list_pending(e2e_client, accountant_token, txn_id)

    # Step 4: Approve
    approved = _step_approve(e2e_client, accountant_token, txn_id)
    assert approved["id"] == txn_id


@pytest.mark.parametrize("stem,vendor_substr,expected_total", INVOICE_CASES[:3])
def test_reject_workflow(stem, vendor_substr, expected_total, e2e_client, e2e_users):
    """
    Alternate path: upload → submit → reject → status=rejected.
    Run for first 3 invoices to cover the rejection path without duplicating all 10.
    """
    uploader_token = _login(e2e_client, "uploader@e2etest.local")
    accountant_token = _login(e2e_client, "accountant@e2etest.local")

    upload_data = _step_upload(e2e_client, uploader_token, stem)
    txn_id = upload_data["transaction"]["id"]

    _step_submit(e2e_client, uploader_token, txn_id)
    _step_list_pending(e2e_client, accountant_token, txn_id)
    _step_reject(e2e_client, accountant_token, txn_id, reason="Duplicate invoice — already processed.")


@pytest.mark.parametrize("stem,vendor_substr,expected_total", INVOICE_CASES[:2])
def test_request_info_then_resubmit_and_approve(stem, vendor_substr, expected_total, e2e_client, e2e_users):
    """
    needs_info path: upload → submit → request_info → needs_info
                     → re-submit → pending_review → approve → accepted.
    """
    uploader_token = _login(e2e_client, "uploader@e2etest.local")
    accountant_token = _login(e2e_client, "accountant@e2etest.local")

    upload_data = _step_upload(e2e_client, uploader_token, stem)
    txn_id = upload_data["transaction"]["id"]

    _step_submit(e2e_client, uploader_token, txn_id)
    _step_list_pending(e2e_client, accountant_token, txn_id)

    # Accountant requests more information
    _step_request_info(e2e_client, accountant_token, txn_id, reason="Please attach the PO number.")

    # Company user re-submits after addressing the query
    resubmitted = _step_submit(e2e_client, uploader_token, txn_id)
    assert resubmitted["status"] == "pending_review"

    # Accountant approves the resubmitted transaction
    _step_approve(e2e_client, accountant_token, txn_id)


# ---------------------------------------------------------------------------
# Auth guard tests (run once, not per-invoice)
# ---------------------------------------------------------------------------

def test_upload_requires_auth(e2e_client, e2e_users):
    """Input: no token. Expected: 401."""
    resp = e2e_client.post(
        "/api/transactions/upload",
        data={"transaction_type": "invoice"},
        files={"file": ("x.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert resp.status_code == 401


def test_company_user_cannot_approve(e2e_client, e2e_users):
    """Input: company_user token on approve endpoint. Expected: 403."""
    uploader_token = _login(e2e_client, "uploader@e2etest.local")

    upload_data = _step_upload(e2e_client, uploader_token, "bajaj_electricals_invoice")
    txn_id = upload_data["transaction"]["id"]
    _step_submit(e2e_client, uploader_token, txn_id)

    resp = e2e_client.post(
        f"/api/transactions/{txn_id}/approve",
        headers={"Authorization": f"Bearer {uploader_token}"},
    )
    assert resp.status_code == 403


def test_company_user_cannot_reject(e2e_client, e2e_users):
    """Input: company_user token on reject endpoint. Expected: 403."""
    uploader_token = _login(e2e_client, "uploader@e2etest.local")

    upload_data = _step_upload(e2e_client, uploader_token, "dhl_logistics_invoice")
    txn_id = upload_data["transaction"]["id"]
    _step_submit(e2e_client, uploader_token, txn_id)

    resp = e2e_client.post(
        f"/api/transactions/{txn_id}/reject",
        headers={"Authorization": f"Bearer {uploader_token}"},
        json={"reason": "testing"},
    )
    assert resp.status_code == 403


def test_double_approve_is_rejected(e2e_client, e2e_users):
    """Approving an already-accepted transaction must return 409 or 422 or 400."""
    uploader_token = _login(e2e_client, "uploader@e2etest.local")
    accountant_token = _login(e2e_client, "accountant@e2etest.local")

    upload_data = _step_upload(e2e_client, uploader_token, "tata_steel_invoice")
    txn_id = upload_data["transaction"]["id"]
    _step_submit(e2e_client, uploader_token, txn_id)
    _step_approve(e2e_client, accountant_token, txn_id)

    # Second approve on an already-accepted transaction
    resp = e2e_client.post(
        f"/api/transactions/{txn_id}/approve",
        headers={"Authorization": f"Bearer {accountant_token}"},
    )
    assert resp.status_code in (409, 422, 400), (
        f"Expected 4xx on double-approve, got {resp.status_code}: {resp.text}"
    )


def test_submit_nonexistent_transaction_returns_404(e2e_client, e2e_users):
    """Submitting a non-existent transaction id must return 404."""
    uploader_token = _login(e2e_client, "uploader@e2etest.local")
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = e2e_client.post(
        f"/api/transactions/{fake_id}/submit",
        headers={"Authorization": f"Bearer {uploader_token}"},
    )
    assert resp.status_code == 404
