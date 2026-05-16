from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import TenantContext
from app.core.security import hash_password
from app.db.models import AuditLog, Company, Firm, PaymentHead, User
from app.schemas.onboarding import (
    CompanyCreate,
    FirmCreate,
    PaymentHeadCreate,
    PaymentHeadOut,
    UserCreate,
)

# {business_type: [(parent_name, [child_names])]}
_TEMPLATES: dict[str, list[tuple[str, list[str]]]] = {
    "manufacturing": [
        ("Raw Materials", ["Steel", "Plastic"]),
        ("Utilities", ["Electricity", "Water"]),
        ("Logistics", ["Transport", "Warehousing"]),
    ],
    "it": [
        ("Salaries", ["Engineering", "Operations"]),
        ("Infrastructure", ["Cloud", "Software Licenses"]),
        ("Office", ["Rent", "Internet"]),
    ],
    "services": [
        ("Salaries", ["Consultants", "Admin"]),
        ("Travel", ["Local", "International"]),
        ("Marketing", ["Digital", "Events"]),
    ],
}


# ---------------------------------------------------------------------------
# Firms
# ---------------------------------------------------------------------------


def create_firm(db: Session, body: FirmCreate, actor_id: uuid.UUID) -> Firm:
    firm = Firm(name=body.name)
    db.add(firm)
    db.flush()
    admin = User(
        email=body.admin_email,
        password_hash=hash_password(body.admin_password),
        role="firm_admin",
        firm_id=firm.id,
    )
    db.add(admin)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    _audit(db, actor_id, "firm.create", firm.id)
    db.commit()
    db.refresh(firm)
    return firm


def list_firms(db: Session) -> list[Firm]:
    return db.query(Firm).order_by(Firm.created_at.desc()).all()


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


def create_company(
    db: Session, ctx: TenantContext, body: CompanyCreate, actor_id: uuid.UUID
) -> Company:
    company = Company(
        firm_id=ctx.firm_id,
        name=body.name,
        business_type=body.business_type,
    )
    db.add(company)
    db.flush()
    _apply_template(db, company.id, body.business_type)
    first_user = User(
        email=body.admin_email,
        password_hash=hash_password(body.admin_password),
        role="company_user",
        firm_id=ctx.firm_id,
        company_id=company.id,
    )
    db.add(first_user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    _audit(db, actor_id, "company.create", company.id)
    db.commit()
    db.refresh(company)
    return company


def list_companies(db: Session, ctx: TenantContext) -> list[Company]:
    return (
        db.query(Company)
        .filter(Company.firm_id == ctx.firm_id)
        .order_by(Company.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Payment heads
# ---------------------------------------------------------------------------


def list_payment_heads(
    db: Session, ctx: TenantContext, company_id: uuid.UUID
) -> list[PaymentHead]:
    _assert_company_scope(ctx, company_id)
    return (
        db.query(PaymentHead)
        .filter(PaymentHead.company_id == company_id)
        .order_by(PaymentHead.created_at)
        .all()
    )


def build_tree(heads: list[PaymentHead]) -> list[PaymentHeadOut]:
    out_map: dict[uuid.UUID, PaymentHeadOut] = {}
    for h in heads:
        out_map[h.id] = PaymentHeadOut(
            id=h.id,
            company_id=h.company_id,
            name=h.name,
            parent_head_id=h.parent_head_id,
            created_at=h.created_at,
            children=[],
        )
    roots: list[PaymentHeadOut] = []
    for h in heads:
        node = out_map[h.id]
        if h.parent_head_id is None:
            roots.append(node)
        else:
            parent = out_map.get(h.parent_head_id)
            if parent is not None:
                parent.children.append(node)
    return roots


def add_payment_head(
    db: Session,
    ctx: TenantContext,
    company_id: uuid.UUID,
    body: PaymentHeadCreate,
    actor_id: uuid.UUID,
) -> PaymentHeadOut:
    _assert_company_scope(ctx, company_id)
    head = PaymentHead(
        company_id=company_id,
        name=body.name,
        parent_head_id=body.parent_head_id,
    )
    db.add(head)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A payment head with this name already exists under the same parent",
        )
    _audit(db, actor_id, "payment_head.create", head.id)
    db.commit()
    db.refresh(head)
    return PaymentHeadOut(
        id=head.id,
        company_id=head.company_id,
        name=head.name,
        parent_head_id=head.parent_head_id,
        created_at=head.created_at,
        children=[],
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


def list_users(
    db: Session, ctx: TenantContext, role: str | None = None
) -> list[User]:
    q = db.query(User).filter(User.firm_id == ctx.firm_id)
    if role:
        q = q.filter(User.role == role)
    return q.order_by(User.created_at.desc()).all()


def create_user(
    db: Session, ctx: TenantContext, body: UserCreate, actor_id: uuid.UUID
) -> User:
    if body.role == "company_user":
        if body.company_id is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "company_id required for company_user",
            )
        _assert_company_scope(ctx, body.company_id)
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        firm_id=ctx.firm_id,
        company_id=body.company_id if body.role == "company_user" else None,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    _audit(db, actor_id, "user.create", user.id)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_template(
    db: Session, company_id: uuid.UUID, business_type: str
) -> None:
    for parent_name, children in _TEMPLATES.get(business_type, []):
        parent = PaymentHead(company_id=company_id, name=parent_name)
        db.add(parent)
        db.flush()
        for child_name in children:
            db.add(
                PaymentHead(
                    company_id=company_id,
                    name=child_name,
                    parent_head_id=parent.id,
                )
            )
    db.flush()


def _assert_company_scope(ctx: TenantContext, company_id: uuid.UUID) -> None:
    if company_id not in ctx.allowed_companies:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Company not in your scope")


def _audit(
    db: Session,
    actor_id: uuid.UUID,
    action: str,
    entity_id: uuid.UUID,
    payload: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_type=action.split(".")[0],
            entity_id=entity_id,
            payload=payload,
        )
    )
