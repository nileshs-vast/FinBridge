from __future__ import annotations

import re
import uuid
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import TenantContext
from app.db.models import AuditLog, Report


async def upload_report(
    db: Session,
    ctx: TenantContext,
    file: UploadFile,
    title: str,
    company_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> Report:
    if company_id not in ctx.allowed_companies:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "company_id not in your scope")

    content = await file.read()
    settings = get_settings()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds size limit"
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(file.filename or "report")
    file_path = upload_dir / f"{uuid4()}_{safe_name}"
    file_path.write_bytes(content)

    report = Report(
        company_id=company_id,
        title=title,
        file_path=str(file_path.relative_to(upload_dir)),
        mime_type=(file.content_type or "application/octet-stream").lower(),
        original_name=file.filename or "report",
        uploaded_by=actor_id,
    )
    db.add(report)
    try:
        db.flush()
    except Exception:
        file_path.unlink(missing_ok=True)
        raise
    _audit(db, actor_id, "report.upload", report.id)
    db.commit()
    db.refresh(report)
    return report


def list_reports(
    db: Session, ctx: TenantContext, company_id_filter: uuid.UUID | None = None
) -> list[Report]:
    companies = ctx.allowed_companies
    q = db.query(Report).filter(Report.company_id.in_(companies))
    if company_id_filter is not None:
        if company_id_filter not in companies:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        q = q.filter(Report.company_id == company_id_filter)
    return q.order_by(Report.created_at.desc()).limit(100).all()


def get_report(db: Session, ctx: TenantContext, report_id: uuid.UUID) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if report.company_id not in ctx.allowed_companies:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_filename(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[^\w.\- ]", "_", name)
    return name[:200] or "report"


def _audit(
    db: Session,
    actor_id: uuid.UUID,
    action: str,
    entity_id: uuid.UUID,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_id,
            action=action,
            entity_type="report",
            entity_id=entity_id,
        )
    )
