from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float
    hsn_sac: str | None = None


class ExtractedInvoice(BaseModel):
    vendor: str | None = None
    vendor_address: str | None = None
    vendor_gstin: str | None = None
    customer_gstin: str | None = None
    place_of_supply: str | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str = "INR"
    subtotal: float | None = None
    tax_amount: float | None = None
    cgst: float | None = None
    sgst: float | None = None
    igst: float | None = None
    reverse_charge: bool = False
    total: float | None = None
    line_items: list[LineItem] = []
    suggested_direction: Literal["purchase", "sales"] | None = None
    confidence: dict[str, float] = {}
    notes: str | None = None
