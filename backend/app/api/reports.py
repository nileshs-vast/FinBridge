from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import TenantContext, current_user, require_role, tenant_scope
from app.db.base import get_db
from app.db.models import User
from app.schemas.reports import ReportOut
from app.services import reports as svc

router = APIRouter(prefix="/reports", tags=["reports"])

_DB = Annotated[Session, Depends(get_db)]
_Ctx = Annotated[TenantContext, Depends(tenant_scope)]
_AnyUser = Annotated[User, Depends(current_user)]
_Accountant = Annotated[User, Depends(require_role("accountant"))]


@router.get("", response_model=list[ReportOut])
def list_reports(
    company_id: uuid.UUID | None = None,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    return [ReportOut.model_validate(r) for r in svc.list_reports(db, ctx, company_id)]


@router.post("", response_model=ReportOut, status_code=201)
async def upload_report(
    file: Annotated[UploadFile, File(...)],
    title: Annotated[str, Form(...)],
    company_id: Annotated[uuid.UUID, Form(...)],
    db: _DB = None,
    ctx: _Ctx = None,
    user: _Accountant = None,
):
    return ReportOut.model_validate(
        await svc.upload_report(db, ctx, file, title, company_id, user.id)
    )


@router.get("/{report_id}/file")
def get_report_file(
    report_id: uuid.UUID,
    db: _DB = None,
    ctx: _Ctx = None,
    _user: _AnyUser = None,
):
    report = svc.get_report(db, ctx, report_id)
    upload_root = Path(get_settings().UPLOAD_DIR).resolve()
    full_path = (upload_root / report.file_path).resolve()
    if not str(full_path).startswith(str(upload_root) + "/"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return FileResponse(
        path=str(full_path),
        media_type=report.mime_type,
        filename=report.original_name,
        headers={"Content-Disposition": f'attachment; filename="{report.original_name}"'},
    )
