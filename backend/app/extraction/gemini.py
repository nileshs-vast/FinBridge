from __future__ import annotations

from pathlib import Path

from .base import ExtractionError
from .schema import ExtractedInvoice


class GeminiProvider:
    """Stub — not yet implemented. Use EXTRACTION_PROVIDER=fixture or =claude."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        raise NotImplementedError(
            "GeminiProvider is not yet implemented. "
            "Set EXTRACTION_PROVIDER=fixture or EXTRACTION_PROVIDER=claude."
        )

    async def extract(self, file_path: Path, mime_type: str) -> ExtractedInvoice:  # pragma: no cover
        raise ExtractionError("GeminiProvider not implemented", retryable=False)
