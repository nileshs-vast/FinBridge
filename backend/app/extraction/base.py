from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .schema import ExtractedInvoice


class ExtractionError(Exception):
    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ExtractionProvider(Protocol):
    name: str

    async def extract(self, file_path: Path, mime_type: str) -> ExtractedInvoice: ...
