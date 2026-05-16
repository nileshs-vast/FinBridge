from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, current_user, tenant_scope
from app.db.base import get_db
from app.db.models import AuditLog, Transaction, User
from app.schemas.audit import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])

_DB = Annotated[Session, Depends(get_db)]
_Ctx = Annotated[TenantContext, Depends(tenant_scope)]
_AnyUser = Annotated[User, Depends(current_user)]


@router.get("", response_model=list[AuditLogOut])
def list_audit(
    entity_id: uuid.UUID | None = None,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    if entity_id is None:
        return []

    txn = db.get(Transaction, entity_id)
    if txn is None or txn.company_id not in ctx.allowed_companies:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    rows = (
        db.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "transaction",
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at)
        )
        .scalars()
        .all()
    )

    return [AuditLogOut.model_validate(r) for r in rows]
