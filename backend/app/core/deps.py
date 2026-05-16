from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.base import get_db
from app.db.models import Company, User

_bearer = HTTPBearer(auto_error=False)
_401 = {"WWW-Authenticate": "Bearer"}


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers=_401,
        )
    try:
        claims = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers=_401,
        ) from exc

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers=_401,
        )

    try:
        uid = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers=_401,
        ) from exc

    user = db.get(User, uid)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers=_401,
        )
    return user


def require_role(*roles: str):
    def _check(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _check


@dataclass
class TenantContext:
    firm_id: uuid.UUID | None
    company_id: uuid.UUID | None
    role: str
    _db: Session = field(repr=False)
    _companies_cache: list[uuid.UUID] | None = field(default=None, repr=False, compare=False)

    @property
    def allowed_companies(self) -> list[uuid.UUID]:
        if self._companies_cache is not None:
            return self._companies_cache
        if self.role == "platform_admin":
            result: list[uuid.UUID] = []  # caller handles the "all" case explicitly
        elif self.role in ("firm_admin", "accountant"):
            rows = self._db.execute(
                select(Company.id).where(Company.firm_id == self.firm_id)
            ).all()
            result = [r[0] for r in rows]
        elif self.role == "company_user" and self.company_id:
            result = [self.company_id]
        else:
            result = []
        self._companies_cache = result
        return result

    @property
    def is_platform_admin(self) -> bool:
        return self.role == "platform_admin"


def tenant_scope(
    user: Annotated[User, Depends(current_user)],
    # FastAPI deduplicates Depends(get_db) by function identity; both current_user
    # and tenant_scope receive the same Session instance within one request.
    db: Annotated[Session, Depends(get_db)],
) -> TenantContext:
    return TenantContext(
        firm_id=user.firm_id,
        company_id=user.company_id,
        role=user.role,
        _db=db,
    )


def get_extraction_provider(request: Request):
    provider = getattr(request.app.state, "extraction_provider", None)
    if provider is None:
        raise RuntimeError("Extraction provider not initialised (lifespan not started)")
    return provider
