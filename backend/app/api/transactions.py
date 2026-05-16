from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import (
    TenantContext,
    current_user,
    get_extraction_provider,
    require_role,
    tenant_scope,
)
from app.db.base import get_db
from app.db.models import User
from app.extraction.base import ExtractionProvider
from app.schemas.transactions import (
    TransactionManualCreate,
    TransactionOut,
    TransactionPatch,
    TransactionReject,
    TransactionRequestInfo,
    TransactionUploadResponse,
)
from app.services import transactions as svc

router = APIRouter(prefix="/transactions", tags=["transactions"])

_DB = Annotated[Session, Depends(get_db)]
_Ctx = Annotated[TenantContext, Depends(tenant_scope)]
_Provider = Annotated[ExtractionProvider, Depends(get_extraction_provider)]
_AnyUser = Annotated[User, Depends(current_user)]
_CompanyUser = Annotated[User, Depends(require_role("company_user"))]
_Accountant = Annotated[User, Depends(require_role("accountant"))]


@router.post("/upload", response_model=TransactionUploadResponse)
async def upload(
    file: Annotated[UploadFile, File(...)],
    transaction_type: Annotated[str, Form(...)],
    direction: Annotated[str | None, Form()] = None,
    company_id: Annotated[uuid.UUID | None, Form()] = None,
    db: _DB = None,
    ctx: _Ctx = None,
    provider: _Provider = None,
    user: _CompanyUser = None,
):
    txn, extracted = await svc.upload_file(
        db, ctx, file, transaction_type, direction, company_id, provider, user.id
    )
    return TransactionUploadResponse(
        transaction=TransactionOut.model_validate(txn),
        extracted=extracted,
    )


@router.post("/manual", response_model=TransactionOut, status_code=201)
def create_manual(
    body: TransactionManualCreate,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _CompanyUser = None,
):
    return TransactionOut.model_validate(svc.create_manual(db, ctx, body, user.id))


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    status: str | None = None,
    type: str | None = None,
    company_id: uuid.UUID | None = None,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    rows = svc.list_transactions(
        db, ctx,
        status_filter=status,
        type_filter=type,
        company_id_filter=company_id,
    )
    return [TransactionOut.model_validate(t) for t in rows]


@router.get("/{txn_id}/attachment")
def get_attachment(
    txn_id: uuid.UUID,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    txn = svc.get_transaction(db, ctx, txn_id)
    att = txn.attachments[0] if txn.attachments else None
    if att is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No attachment")
    upload_root = Path(get_settings().UPLOAD_DIR).resolve()
    full_path = (upload_root / att.file_path).resolve()
    if not str(full_path).startswith(str(upload_root) + "/"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return FileResponse(
        path=str(full_path),
        media_type=att.mime_type,
        filename=att.original_name,
        headers={"Content-Disposition": f'attachment; filename="{att.original_name}"'},
    )


@router.get("/{txn_id}", response_model=TransactionOut)
def get_transaction(
    txn_id: uuid.UUID,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    return TransactionOut.model_validate(svc.get_transaction(db, ctx, txn_id))


@router.patch("/{txn_id}", response_model=TransactionOut)
def patch_transaction(
    txn_id: uuid.UUID,
    body: TransactionPatch,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _AnyUser = None,
):
    return TransactionOut.model_validate(svc.patch_transaction(db, ctx, txn_id, body, user.id))


@router.post("/{txn_id}/submit", response_model=TransactionOut)
def submit_transaction(
    txn_id: uuid.UUID,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _CompanyUser = None,
):
    return TransactionOut.model_validate(svc.submit_transaction(db, ctx, txn_id, user.id))


@router.post("/{txn_id}/approve", response_model=TransactionOut)
def approve_transaction(
    txn_id: uuid.UUID,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _Accountant = None,
):
    return TransactionOut.model_validate(svc.approve_transaction(db, ctx, txn_id, user.id))


@router.post("/{txn_id}/reject", response_model=TransactionOut)
def reject_transaction(
    txn_id: uuid.UUID,
    body: TransactionReject,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _Accountant = None,
):
    return TransactionOut.model_validate(
        svc.reject_transaction(db, ctx, txn_id, body.reason, user.id)
    )


@router.post("/{txn_id}/request-info", response_model=TransactionOut)
def request_info(
    txn_id: uuid.UUID,
    body: TransactionRequestInfo,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _Accountant = None,
):
    return TransactionOut.model_validate(
        svc.request_info(db, ctx, txn_id, body.reason, user.id)
    )
