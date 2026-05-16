from __future__ import annotations

import asyncio
from pathlib import Path

from .base import ExtractionError
from .schema import ExtractedInvoice

_PROMPT = (
    "Extract all invoice details from this document. "
    "Return a JSON object with exactly these fields: "
    "vendor, vendor_address, vendor_gstin, customer_gstin, place_of_supply, "
    "invoice_no, invoice_date (YYYY-MM-DD or null), due_date (YYYY-MM-DD or null), "
    "currency (default INR), subtotal, tax_amount, cgst, sgst, igst, "
    "reverse_charge (true/false), total, "
    "line_items (array of {description, quantity, unit_price, amount, hsn_sac}), "
    "suggested_direction ('purchase' or 'sales' or null), "
    "confidence (object mapping field names to float 0.0-1.0 based on legibility), "
    "notes. Use null for any missing or unclear fields."
)


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        try:
            from google import genai  # type: ignore[import-untyped]
            from google.genai import types as _types  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "google-genai is not installed. "
                "Run: pip install 'google-genai==0.3.0'"
            ) from exc
        self._client = genai.Client(api_key=api_key)
        self._types = _types
        self._model = model

    async def extract(self, file_path: Path, mime_type: str) -> ExtractedInvoice:
        return await asyncio.to_thread(self._extract_sync, file_path, mime_type)

    def _extract_sync(self, file_path: Path, mime_type: str) -> ExtractedInvoice:
        types = self._types
        file_bytes = file_path.read_bytes()

        part = types.Part(
            inline_data=types.Blob(data=file_bytes, mime_type=mime_type)
        )

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[part, _PROMPT],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
        except Exception as exc:
            raise ExtractionError(str(exc), retryable=False) from exc

        text = (response.text or "").strip()
        if not text:
            raise ExtractionError("Gemini returned empty response", retryable=True)

        try:
            return ExtractedInvoice.model_validate_json(text)
        except Exception as exc:
            raise ExtractionError(f"Gemini JSON parse failed: {exc}") from exc
