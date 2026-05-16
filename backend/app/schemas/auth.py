from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    firm_id: uuid.UUID | None
    company_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until token expiry
    user: UserOut
