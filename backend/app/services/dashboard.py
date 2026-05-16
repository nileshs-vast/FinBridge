from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.deps import TenantContext
from app.db.models import PaymentHead, Transaction
from app.schemas.dashboard import DashboardSummary, ExpenseHeadStat, StatusCount
from app.schemas.transactions import TransactionOut


def get_summary(db: Session, ctx: TenantContext) -> DashboardSummary:
    _empty = DashboardSummary(
        counts_by_status=[], top_expense_heads=[], recent_transactions=[]
    )

    if ctx.is_platform_admin:
        return _empty

    companies = ctx.allowed_companies
    if not companies:
        return _empty

    status_rows = (
        db.query(Transaction.status, func.count(Transaction.id))
        .filter(Transaction.company_id.in_(companies))
        .group_by(Transaction.status)
        .all()
    )
    counts = [StatusCount(status=r[0], count=r[1]) for r in status_rows]

    head_rows = (
        db.query(
            Transaction.payment_head_id,
            PaymentHead.name,
            func.sum(Transaction.amount),
        )
        .join(PaymentHead, Transaction.payment_head_id == PaymentHead.id)
        .filter(
            Transaction.company_id.in_(companies),
            Transaction.status == "accepted",
            Transaction.payment_head_id.isnot(None),
        )
        .group_by(Transaction.payment_head_id, PaymentHead.name)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(5)
        .all()
    )
    top_heads = [
        ExpenseHeadStat(
            payment_head_id=r[0],
            name=r[1],
            total_amount=Decimal(str(r[2] or 0)),
        )
        for r in head_rows
    ]

    recent_txns = (
        db.query(Transaction)
        .options(selectinload(Transaction.attachments))
        .filter(Transaction.company_id.in_(companies))
        .order_by(Transaction.created_at.desc())
        .limit(10)
        .all()
    )
    recent = [TransactionOut.model_validate(t) for t in recent_txns]

    return DashboardSummary(
        counts_by_status=counts,
        top_expense_heads=top_heads,
        recent_transactions=recent,
    )
