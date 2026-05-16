from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.extraction.schema import ExtractedInvoice


class AttachmentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class TransactionOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    company_id: uuid.UUID
    transaction_type: str
    direction: str | None
    vendor: str | None
    invoice_no: str | None
    transaction_date: date | None
    amount: Decimal | None
    currency: str
    payment_head_id: uuid.UUID | None
    status: str
    raw_extraction: dict | None
    notes: str | None
    rejection_reason: str | None
    info_request_reason: str | None
    possible_duplicate_of: uuid.UUID | None
    uploaded_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    created_at: datetime
    reviewed_at: datetime | None
    attachments: list[AttachmentOut] = []


class TransactionUploadResponse(BaseModel):
    transaction: TransactionOut
    extracted: ExtractedInvoice


class TransactionManualCreate(BaseModel):
    transaction_type: str
    direction: str | None = None
    vendor: str | None = None
    invoice_no: str | None = None
    transaction_date: date | None = None
    amount: Decimal | None = None
    currency: str = "INR"
    payment_head_id: uuid.UUID | None = None
    notes: str | None = None
    company_id: uuid.UUID | None = None


class TransactionPatch(BaseModel):
    direction: str | None = None
    vendor: str | None = None
    invoice_no: str | None = None
    transaction_date: date | None = None
    amount: Decimal | None = None
    currency: str | None = None
    payment_head_id: uuid.UUID | None = None
    notes: str | None = None


class TransactionReject(BaseModel):
    reason: str = Field(..., min_length=1)


class TransactionRequestInfo(BaseModel):
    reason: str = Field(..., min_length=1)
