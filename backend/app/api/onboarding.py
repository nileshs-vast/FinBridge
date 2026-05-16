from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, current_user, require_role, tenant_scope
from app.db.base import get_db
from app.db.models import User
from app.schemas.onboarding import (
    CompanyCreate,
    CompanyOut,
    FirmCreate,
    FirmOut,
    PaymentHeadCreate,
    PaymentHeadOut,
    UserCreate,
    UserOut,
)
from app.services import onboarding as svc

router = APIRouter(tags=["onboarding"])

_DB = Annotated[Session, Depends(get_db)]
_Ctx = Annotated[TenantContext, Depends(tenant_scope)]
_AnyUser = Annotated[User, Depends(current_user)]
_PlatformAdmin = Annotated[User, Depends(require_role("platform_admin"))]
_FirmAdmin = Annotated[User, Depends(require_role("firm_admin"))]
_FirmOrAccountant = Annotated[User, Depends(require_role("firm_admin", "accountant"))]


# ---------------------------------------------------------------------------
# Firms  (platform_admin only)
# ---------------------------------------------------------------------------


@router.get("/firms", response_model=list[FirmOut])
def list_firms(db: _DB = None, _user: _PlatformAdmin = None):
    return [FirmOut.model_validate(f) for f in svc.list_firms(db)]


@router.post("/firms", response_model=FirmOut, status_code=201)
def create_firm(body: FirmCreate, db: _DB = None, user: _PlatformAdmin = None):
    return FirmOut.model_validate(svc.create_firm(db, body, user.id))


# ---------------------------------------------------------------------------
# Companies  (firm_admin writes, firm_admin|accountant reads)
# ---------------------------------------------------------------------------


@router.get("/companies", response_model=list[CompanyOut])
def list_companies(
    db: _DB = None, ctx: _Ctx = None, _user: _FirmOrAccountant = None
):
    return [CompanyOut.model_validate(c) for c in svc.list_companies(db, ctx)]


@router.post("/companies", response_model=CompanyOut, status_code=201)
def create_company(
    body: CompanyCreate,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _FirmAdmin = None,
):
    return CompanyOut.model_validate(svc.create_company(db, ctx, body, user.id))


@router.get(
    "/companies/{company_id}/payment-heads", response_model=list[PaymentHeadOut]
)
def list_payment_heads(
    company_id: uuid.UUID,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    heads = svc.list_payment_heads(db, ctx, company_id)
    return svc.build_tree(heads)


@router.post(
    "/companies/{company_id}/payment-heads",
    response_model=PaymentHeadOut,
    status_code=201,
)
def add_payment_head(
    company_id: uuid.UUID,
    body: PaymentHeadCreate,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _FirmAdmin = None,
):
    return svc.add_payment_head(db, ctx, company_id, body, user.id)


# ---------------------------------------------------------------------------
# Users  (firm_admin only)
# ---------------------------------------------------------------------------


@router.get("/users", response_model=list[UserOut])
def list_users(
    role: str | None = None,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _FirmAdmin = None,
):
    return [UserOut.model_validate(u) for u in svc.list_users(db, ctx, role)]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    db: _DB = None,
    ctx: _Ctx = None,
    user: _FirmAdmin = None,
):
    return UserOut.model_validate(svc.create_user(db, ctx, body, user.id))
