from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, current_user, tenant_scope
from app.db.base import get_db
from app.db.models import User
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard as svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_DB = Annotated[Session, Depends(get_db)]
_Ctx = Annotated[TenantContext, Depends(tenant_scope)]
_AnyUser = Annotated[User, Depends(current_user)]


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: _DB = None, ctx: _Ctx = None, _user: _AnyUser = None):
    return svc.get_summary(db, ctx)
