from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    company_id: uuid.UUID
    title: str
    original_name: str
    mime_type: str
    uploaded_by: uuid.UUID
    created_at: datetime
