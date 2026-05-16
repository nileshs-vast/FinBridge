"""
Idempotent seed script for FinBridge demo data.
Run inside the app container: python -m app.seeds.run
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import SessionLocal
from app.db.models import (
    Attachment,
    Company,
    Firm,
    PaymentHead,
    Report,
    Transaction,
    User,
)
from app.seeds.payment_head_templates import TEMPLATES

_NS = uuid.NAMESPACE_DNS
PASSWORD = "Finbridge#2026"


def _uid(name: str) -> uuid.UUID:
    return uuid.uuid5(_NS, f"finbridge-seed-{name}")


# ---------------------------------------------------------------------------
# Deterministic IDs
# ---------------------------------------------------------------------------

FIRM_ID = _uid("sharma-co")

ACME_ID = _uid("acme-manufacturing")
LUMEN_ID = _uid("lumen-it")

U_PLATFORM = _uid("platform-admin")
U_FIRM_ADMIN = _uid("firm-admin")
U_PRIYA = _uid("priya-accountant")
U_RAHUL = _uid("rahul-accountant")
U_ACME = _uid("acme-upload")
U_LUMEN = _uid("lumen-upload")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ---------------------------------------------------------------------------
# Individual seeders
# ---------------------------------------------------------------------------


def _upsert(db, obj) -> None:
    """Insert if the row doesn't exist; skip on re-runs.
    Avoids db.merge() which NULLs server-default columns (created_at) on UPDATE.
    """
    if db.get(type(obj), obj.id) is None:
        db.add(obj)


def seed_firms(db) -> None:
    _upsert(db, Firm(id=FIRM_ID, name="Sharma & Co."))


def seed_companies(db) -> None:
    _upsert(db, Company(id=ACME_ID, firm_id=FIRM_ID, name="Acme Manufacturing", business_type="manufacturing"))
    _upsert(db, Company(id=LUMEN_ID, firm_id=FIRM_ID, name="Lumen IT", business_type="it"))


def _ph_parent_id(btype: str, parent_name: str) -> uuid.UUID:
    """Return the deterministic UUID for a top-level payment head by name."""
    for i, p in enumerate(TEMPLATES[btype]):
        if p["name"] == parent_name:
            return _uid(f"ph-{btype}-{i}")
    raise KeyError(f"Payment head parent '{parent_name}' not found in {btype} template")


def _ph_child_id(btype: str, parent_name: str, child_name: str) -> uuid.UUID:
    """Return the deterministic UUID for a child payment head by name."""
    for i, p in enumerate(TEMPLATES[btype]):
        if p["name"] == parent_name:
            for j, c in enumerate(p.get("children", [])):
                if c["name"] == child_name:
                    return _uid(f"ph-{btype}-{i}-{j}")
    raise KeyError(f"Payment head '{parent_name} → {child_name}' not found in {btype} template")


def seed_payment_heads(db) -> None:
    for company_id, btype in [(ACME_ID, "manufacturing"), (LUMEN_ID, "it")]:
        for i, head_def in enumerate(TEMPLATES[btype]):
            parent_id = _uid(f"ph-{btype}-{i}")
            _upsert(
                db,
                PaymentHead(
                    id=parent_id,
                    company_id=company_id,
                    name=head_def["name"],
                    parent_head_id=None,
                ),
            )
            for j, child_def in enumerate(head_def.get("children", [])):
                child_id = _uid(f"ph-{btype}-{i}-{j}")
                _upsert(
                    db,
                    PaymentHead(
                        id=child_id,
                        company_id=company_id,
                        name=child_def["name"],
                        parent_head_id=parent_id,
                    ),
                )


def seed_users(db) -> None:
    pw = hash_password(PASSWORD)
    users = [
        User(id=U_PLATFORM, email="platform@finbridge.local", password_hash=pw, role="platform_admin", firm_id=None, company_id=None),
        User(id=U_FIRM_ADMIN, email="admin@sharmaco.local", password_hash=pw, role="firm_admin", firm_id=FIRM_ID, company_id=None),
        User(id=U_PRIYA, email="priya@sharmaco.local", password_hash=pw, role="accountant", firm_id=FIRM_ID, company_id=None),
        User(id=U_RAHUL, email="rahul@sharmaco.local", password_hash=pw, role="accountant", firm_id=FIRM_ID, company_id=None),
        User(id=U_ACME, email="upload@acme.local", password_hash=pw, role="company_user", firm_id=FIRM_ID, company_id=ACME_ID),
        User(id=U_LUMEN, email="upload@lumenit.local", password_hash=pw, role="company_user", firm_id=FIRM_ID, company_id=LUMEN_ID),
    ]
    for u in users:
        _upsert(db, u)


def _raw_extraction(
    vendor: str,
    invoice_no: str,
    total: float,
    vendor_gstin: str | None = None,
) -> dict:
    subtotal = round(total / 1.18, 2)
    tax = round(total - subtotal, 2)
    half_tax = round(tax / 2, 2)
    return {
        "vendor": vendor,
        "vendor_address": None,
        "vendor_gstin": vendor_gstin,
        "customer_gstin": "27AAACA1234B1Z5",
        "place_of_supply": "27",
        "invoice_no": invoice_no,
        "invoice_date": "2024-04-15",
        "due_date": None,
        "currency": "INR",
        "subtotal": subtotal,
        "tax_amount": tax,
        "cgst": half_tax,
        "sgst": half_tax,
        "igst": None,
        "reverse_charge": False,
        "total": total,
        "line_items": [
            {
                "description": "Goods/Services",
                "quantity": 1.0,
                "unit_price": subtotal,
                "amount": subtotal,
                "hsn_sac": "7208",
            }
        ],
        "suggested_direction": "purchase",
        "confidence": {"vendor": 0.95, "total": 0.98, "invoice_date": 0.92, "invoice_no": 0.96},
        "notes": None,
    }


def _placeholder_file(upload_dir: Path, stem: str) -> tuple[str, str]:
    """Write a small placeholder text file; return (relative_path, original_name)."""
    upload_dir.mkdir(parents=True, exist_ok=True)
    fname = f"seed_{stem}.txt"
    fpath = upload_dir / fname
    if not fpath.exists():
        fpath.write_text(f"[FinBridge demo placeholder: {stem}]\n")
    return fname, f"{stem}.pdf"


def _file_size(upload_dir: Path, rel_path: str) -> int:
    try:
        return (upload_dir / rel_path).stat().st_size
    except FileNotFoundError:
        return 0


def seed_transactions(db, upload_dir: Path) -> None:
    now = _now()

    steel_id = _ph_child_id("manufacturing", "Raw Materials", "Steel")
    electricity_id = _ph_child_id("manufacturing", "Utilities", "Electricity")
    transport_id = _ph_child_id("manufacturing", "Logistics", "Transport")

    txns = [
        # --- Accepted invoices (3) ---
        {
            "id": _uid("txn-accepted-tata"),
            "status": "accepted",
            "vendor": "Tata Steel Ltd",
            "invoice_no": "TATA/2024/001",
            "transaction_date": date(2024, 4, 5),
            "amount": Decimal("495600.00"),
            "payment_head_id": steel_id,
            "reviewed_by": U_PRIYA,
            "reviewed_at": now,
            "raw_extraction": _raw_extraction("Tata Steel Ltd", "TATA/2024/001", 495600.0, "27AAACT2727Q1ZW"),
        },
        {
            "id": _uid("txn-accepted-bel"),
            "status": "accepted",
            "vendor": "Bharat Electricals Ltd",
            "invoice_no": "BEL/2024/042",
            "transaction_date": date(2024, 4, 10),
            "amount": Decimal("118000.00"),
            "payment_head_id": electricity_id,
            "reviewed_by": U_PRIYA,
            "reviewed_at": now,
            "raw_extraction": _raw_extraction("Bharat Electricals Ltd", "BEL/2024/042", 118000.0, "29AABCB1234C1Z7"),
        },
        {
            "id": _uid("txn-accepted-dhl"),
            "status": "accepted",
            "vendor": "DHL Logistics",
            "invoice_no": "DHL/2024/789",
            "transaction_date": date(2024, 4, 12),
            "amount": Decimal("59000.00"),
            "payment_head_id": transport_id,
            "reviewed_by": U_RAHUL,
            "reviewed_at": now,
            "raw_extraction": _raw_extraction("DHL Logistics", "DHL/2024/789", 59000.0),
        },
        # --- Accepted salary register (1) ---
        {
            "id": _uid("txn-accepted-salary"),
            "status": "accepted",
            "transaction_type": "salary_register",
            "direction": None,
            "vendor": "Acme Manufacturing Staff",
            "invoice_no": "SAL/APR/2024",
            "transaction_date": date(2024, 4, 30),
            "amount": Decimal("1250000.00"),
            "payment_head_id": None,
            "reviewed_by": U_PRIYA,
            "reviewed_at": now,
            "raw_extraction": None,
        },
        # --- Pending review (4) ---
        {
            "id": _uid("txn-pending-mahindra"),
            "status": "pending_review",
            "vendor": "Mahindra Logistics",
            "invoice_no": "ML/2024/112",
            "transaction_date": date(2024, 5, 2),
            "amount": Decimal("84100.00"),
            "payment_head_id": None,
            "raw_extraction": _raw_extraction("Mahindra Logistics", "ML/2024/112", 84100.0),
        },
        {
            "id": _uid("txn-pending-lt"),
            "status": "pending_review",
            "vendor": "Larsen & Toubro Ltd",
            "invoice_no": "LT/2024/555",
            "transaction_date": date(2024, 5, 5),
            "amount": Decimal("236000.00"),
            "payment_head_id": None,
            "raw_extraction": _raw_extraction("Larsen & Toubro Ltd", "LT/2024/555", 236000.0, "27AABCL0107N1ZJ"),
        },
        {
            "id": _uid("txn-pending-bajaj"),
            "status": "pending_review",
            "vendor": "Bajaj Electricals",
            "invoice_no": "BE/2024/209",
            "transaction_date": date(2024, 5, 8),
            "amount": Decimal("47200.00"),
            "payment_head_id": None,
            "raw_extraction": _raw_extraction("Bajaj Electricals", "BE/2024/209", 47200.0),
        },
        {
            "id": _uid("txn-pending-sail"),
            "status": "pending_review",
            "vendor": "SAIL — Steel Authority of India",
            "invoice_no": "SAIL/2024/311",
            "transaction_date": date(2024, 5, 10),
            "amount": Decimal("325000.00"),
            "payment_head_id": None,
            "raw_extraction": _raw_extraction("SAIL — Steel Authority of India", "SAIL/2024/311", 325000.0, "07AAACS4659Q1ZA"),
        },
        # --- Draft AI (2) ---
        {
            "id": _uid("txn-draft-wipro"),
            "status": "draft_ai",
            "vendor": "Wipro Infrastructure",
            "invoice_no": "WIPRO/2024/088",
            "transaction_date": date(2024, 5, 12),
            "amount": Decimal("92000.00"),
            "payment_head_id": None,
            "raw_extraction": _raw_extraction("Wipro Infrastructure", "WIPRO/2024/088", 92000.0, "29AABCW0140G1ZK"),
        },
        {
            "id": _uid("txn-draft-ultratech"),
            "status": "draft_ai",
            "vendor": "Ultratech Cement",
            "invoice_no": "UTC/2024/199",
            "transaction_date": date(2024, 5, 14),
            "amount": Decimal("141600.00"),
            "payment_head_id": None,
            "raw_extraction": _raw_extraction("Ultratech Cement", "UTC/2024/199", 141600.0),
        },
    ]

    for data in txns:
        txn_id: uuid.UUID = data["id"]
        stem = f"invoice_{txn_id.hex[:8]}"
        rel_path, orig_name = _placeholder_file(upload_dir, stem)

        txn = Transaction(
            id=txn_id,
            company_id=ACME_ID,
            transaction_type=data.get("transaction_type", "invoice"),
            direction=data.get("direction", "purchase"),
            vendor=data.get("vendor"),
            invoice_no=data.get("invoice_no"),
            transaction_date=data.get("transaction_date"),
            amount=data.get("amount"),
            currency="INR",
            payment_head_id=data.get("payment_head_id"),
            status=data["status"],
            raw_extraction=data.get("raw_extraction"),
            uploaded_by=U_ACME,
            reviewed_by=data.get("reviewed_by"),
            reviewed_at=data.get("reviewed_at"),
        )
        _upsert(db, txn)

        att_id = _uid(f"att-{txn_id}")
        att = Attachment(
            id=att_id,
            transaction_id=txn_id,
            file_path=rel_path,
            mime_type="text/plain",
            original_name=orig_name,
            size_bytes=_file_size(upload_dir, rel_path),
        )
        _upsert(db, att)


def seed_reports(db, upload_dir: Path) -> None:
    report_id = _uid("report-april-mis")
    rel_path, _ = _placeholder_file(upload_dir, "april_2024_mis")

    _upsert(
        db,
        Report(
            id=report_id,
            company_id=ACME_ID,
            title="April 2024 MIS Report",
            file_path=rel_path,
            mime_type="text/plain",
            original_name="April_2024_MIS_Report.pdf",
            uploaded_by=U_PRIYA,
        ),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)

    db = SessionLocal()
    try:
        seed_firms(db)
        seed_companies(db)
        db.flush()

        seed_payment_heads(db)
        seed_users(db)
        db.flush()

        seed_transactions(db, upload_dir)
        seed_reports(db, upload_dir)

        db.commit()

        print("✓ Seed complete")
        print("  Firm:    Sharma & Co.")
        print("  Companies: Acme Manufacturing, Lumen IT")
        print("  Users (password: Finbridge#2026):")
        print("    platform@finbridge.local  — platform_admin")
        print("    admin@sharmaco.local      — firm_admin")
        print("    priya@sharmaco.local      — accountant")
        print("    rahul@sharmaco.local      — accountant")
        print("    upload@acme.local         — company_user (Acme)")
        print("    upload@lumenit.local      — company_user (Lumen IT)")
        print("  Transactions: 4 accepted, 4 pending_review, 2 draft_ai")
        print("  Reports: 1 MIS report (Acme Manufacturing)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
