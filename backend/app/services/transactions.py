from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.deps import TenantContext
from app.db.models import Attachment, AuditLog, Transaction
from app.extraction.base import ExtractionError, ExtractionProvider
from app.extraction.schema import ExtractedInvoice
from app.schemas.transactions import TransactionManualCreate, TransactionPatch

_ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "application/pdf",
}

_EDITABLE_STATUSES = {"draft_ai", "pending_review", "needs_info"}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


async def upload_file(
    db: Session,
    ctx: TenantContext,
    file: UploadFile,
    transaction_type: str,
    direction: str | None,
    company_id: uuid.UUID | None,
    provider: ExtractionProvider,
    actor_id: uuid.UUID,
) -> tuple[Transaction, ExtractedInvoice]:
    mime = (file.content_type or "").lower()
    if mime not in _ALLOWED_MIME:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {mime!r}")

    content = await file.read()
    settings = get_settings()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10 MB limit")

    resolved_cid = _resolve_company_id(ctx, company_id)

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(file.filename or "upload")
    file_path = upload_dir / f"{uuid4()}_{safe_name}"
    file_path.write_bytes(content)

    extracted = ExtractedInvoice()
    raw_extraction: dict = {}
    try:
        extracted = await provider.extract(file_path, mime)
        raw_extraction = extracted.model_dump(mode="json")
    except ExtractionError as exc:
        raw_extraction = {"error": str(exc)}

    txn = Transaction(
        company_id=resolved_cid,
        transaction_type=transaction_type,
        direction=direction or extracted.suggested_direction,
        vendor=extracted.vendor,
        invoice_no=extracted.invoice_no,
        transaction_date=extracted.invoice_date,
        amount=extracted.total,
        currency=extracted.currency or "INR",
        status="draft_ai",
        raw_extraction=raw_extraction,
        uploaded_by=actor_id,
    )
    db.add(txn)
    try:
        db.flush()
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    db.add(Attachment(
        transaction_id=txn.id,
        file_path=str(file_path.relative_to(upload_dir)),
        mime_type=mime,
        original_name=file.filename or "upload",
        size_bytes=len(content),
    ))
    _audit(db, actor_id, "transaction.upload", txn.id)
    db.commit()
    db.refresh(txn)
    return txn, extracted


# ---------------------------------------------------------------------------
# Manual entry
# ---------------------------------------------------------------------------


def create_manual(
    db: Session,
    ctx: TenantContext,
    body: TransactionManualCreate,
    actor_id: uuid.UUID,
) -> Transaction:
    resolved_cid = _resolve_company_id(ctx, body.company_id)
    txn = Transaction(
        company_id=resolved_cid,
        transaction_type=body.transaction_type,
        direction=body.direction,
        vendor=body.vendor,
        invoice_no=body.invoice_no,
        transaction_date=body.transaction_date,
        amount=body.amount,
        currency=body.currency,
        payment_head_id=body.payment_head_id,
        notes=body.notes,
        status="pending_review",
        uploaded_by=actor_id,
    )
    db.add(txn)
    db.flush()
    _audit(db, actor_id, "transaction.manual", txn.id)
    db.commit()
    db.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def list_transactions(
    db: Session,
    ctx: TenantContext,
    *,
    status_filter: str | None = None,
    type_filter: str | None = None,
    company_id_filter: uuid.UUID | None = None,
) -> list[Transaction]:
    if ctx.is_platform_admin:
        return []

    companies = ctx.allowed_companies
    q = (
        db.query(Transaction)
        .options(selectinload(Transaction.attachments))
        .filter(Transaction.company_id.in_(companies))
    )
    if status_filter:
        q = q.filter(Transaction.status == status_filter)
    if type_filter:
        q = q.filter(Transaction.transaction_type == type_filter)
    if company_id_filter:
        if company_id_filter not in companies:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        q = q.filter(Transaction.company_id == company_id_filter)

    return q.order_by(Transaction.created_at.desc()).limit(100).all()


def get_transaction(db: Session, ctx: TenantContext, txn_id: uuid.UUID) -> Transaction:
    txn = (
        db.query(Transaction)
        .options(selectinload(Transaction.attachments))
        .filter(Transaction.id == txn_id)
        .first()
    )
    if txn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    if txn.company_id not in ctx.allowed_companies:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return txn


# ---------------------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------------------


def patch_transaction(
    db: Session,
    ctx: TenantContext,
    txn_id: uuid.UUID,
    body: TransactionPatch,
    actor_id: uuid.UUID,
) -> Transaction:
    txn = _get_owned_txn(db, ctx, txn_id)
    if txn.status not in _EDITABLE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot edit transaction with status '{txn.status}'")
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(txn, field, value)
    _audit(db, actor_id, "transaction.patch", txn.id, payload=body.model_dump(mode="json", exclude_unset=True))
    db.commit()
    db.refresh(txn)
    return txn


def submit_transaction(
    db: Session,
    ctx: TenantContext,
    txn_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Transaction:
    txn = _get_owned_txn(db, ctx, txn_id)
    if txn.status not in ("draft_ai", "needs_info"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot submit from status '{txn.status}'")

    if txn.vendor and txn.invoice_no:
        dup = (
            db.query(Transaction)
            .filter(
                Transaction.company_id == txn.company_id,
                Transaction.vendor == txn.vendor,
                Transaction.invoice_no == txn.invoice_no,
                Transaction.status == "accepted",
                Transaction.id != txn.id,
            )
            .first()
        )
        if dup:
            txn.possible_duplicate_of = dup.id

    txn.status = "pending_review"
    _audit(db, actor_id, "transaction.submit", txn.id)
    db.commit()
    db.refresh(txn)
    return txn


def approve_transaction(
    db: Session,
    ctx: TenantContext,
    txn_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Transaction:
    txn = _get_owned_txn(db, ctx, txn_id)
    if txn.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot approve from status '{txn.status}'")
    txn.status = "accepted"
    txn.reviewed_by = actor_id
    txn.reviewed_at = datetime.now(timezone.utc)
    _audit(db, actor_id, "transaction.approve", txn.id)
    db.commit()
    db.refresh(txn)
    return txn


def reject_transaction(
    db: Session,
    ctx: TenantContext,
    txn_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID,
) -> Transaction:
    txn = _get_owned_txn(db, ctx, txn_id)
    if txn.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot reject from status '{txn.status}'")
    txn.status = "rejected"
    txn.rejection_reason = reason
    txn.reviewed_by = actor_id
    txn.reviewed_at = datetime.now(timezone.utc)
    _audit(db, actor_id, "transaction.reject", txn.id)
    db.commit()
    db.refresh(txn)
    return txn


def request_info(
    db: Session,
    ctx: TenantContext,
    txn_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID,
) -> Transaction:
    txn = _get_owned_txn(db, ctx, txn_id)
    if txn.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot request info from status '{txn.status}'")
    txn.status = "needs_info"
    txn.info_request_reason = reason
    _audit(db, actor_id, "transaction.request_info", txn.id)
    db.commit()
    db.refresh(txn)
    return txn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_owned_txn(db: Session, ctx: TenantContext, txn_id: uuid.UUID) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    if txn.company_id not in ctx.allowed_companies:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return txn


def _resolve_company_id(ctx: TenantContext, company_id: uuid.UUID | None) -> uuid.UUID:
    if ctx.role == "company_user":
        if ctx.company_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "User has no company assigned")
        return ctx.company_id
    if company_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "company_id required for this role")
    if company_id not in ctx.allowed_companies:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "company_id not in your firm")
    return company_id


def _safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.\- ]", "_", name)
    return name[:200] or "upload"


def _audit(
    db: Session,
    actor_id: uuid.UUID,
    action: str,
    entity_id: uuid.UUID,
    payload: dict | None = None,
) -> None:
    db.add(AuditLog(
        actor_user_id=actor_id,
        action=action,
        entity_type="transaction",
        entity_id=entity_id,
        payload=payload,
    ))
