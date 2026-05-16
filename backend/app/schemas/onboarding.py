from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FirmCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    admin_email: str = Field(..., min_length=3, max_length=320)
    admin_password: str = Field(..., min_length=6)


class FirmOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    created_at: datetime


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    business_type: Literal["manufacturing", "it", "services"]
    admin_email: str = Field(..., min_length=3, max_length=320)
    admin_password: str = Field(..., min_length=6)


class CompanyOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    firm_id: uuid.UUID
    name: str
    business_type: str
    created_at: datetime


class PaymentHeadCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    parent_head_id: uuid.UUID | None = None


class PaymentHeadOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    company_id: uuid.UUID
    name: str
    parent_head_id: uuid.UUID | None
    created_at: datetime
    children: list[PaymentHeadOut] = []


PaymentHeadOut.model_rebuild()


class UserCreate(BaseModel):
    role: Literal["accountant", "company_user"]
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=6)
    company_id: uuid.UUID | None = None


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    role: str
    firm_id: uuid.UUID | None
    company_id: uuid.UUID | None
    created_at: datetime
