from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.transactions import TransactionOut


class StatusCount(BaseModel):
    status: str
    count: int


class ExpenseHeadStat(BaseModel):
    payment_head_id: uuid.UUID
    name: str
    total_amount: Decimal


class DashboardSummary(BaseModel):
    counts_by_status: list[StatusCount]
    top_expense_heads: list[ExpenseHeadStat]
    recent_transactions: list[TransactionOut]
