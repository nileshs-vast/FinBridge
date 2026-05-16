from __future__ import annotations

import base64
from pathlib import Path

import anthropic

from .base import ExtractionError
from .schema import ExtractedInvoice

_TOOL_NAME = "extract_invoice"


class ClaudeProvider:
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._tool = _build_tool()

    async def extract(self, file_path: Path, mime_type: str) -> ExtractedInvoice:
        b64 = base64.standard_b64encode(file_path.read_bytes()).decode()

        if mime_type == "application/pdf":
            file_block: dict = {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
            }
        else:
            file_block = {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": b64},
            }

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                tools=[self._tool],
                tool_choice={"type": "tool", "name": _TOOL_NAME},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            file_block,
                            {
                                "type": "text",
                                "text": (
                                    "Extract all invoice details from this document. "
                                    "Include Indian GST fields (GSTIN, HSN/SAC, CGST/SGST/IGST) "
                                    "where present. Set confidence scores 0.0–1.0 per field based "
                                    "on how clearly the value is legible. Use null for missing fields."
                                ),
                            },
                        ],
                    }
                ],
            )
        except anthropic.APIError as exc:
            raise ExtractionError(str(exc), retryable=_is_retryable(exc)) from exc

        for block in response.content:
            if block.type == "tool_use" and block.name == _TOOL_NAME:
                try:
                    return ExtractedInvoice.model_validate(block.input)
                except Exception as exc:
                    raise ExtractionError(f"Schema validation failed: {exc}") from exc

        raise ExtractionError("Claude returned no tool_use block", retryable=False)


def _build_tool() -> dict:
    schema = ExtractedInvoice.model_json_schema()
    # Anthropic doesn't resolve $ref — inline $defs so Claude sees the full LineItem structure
    defs = schema.pop("$defs", {})
    _inline_refs(schema, defs)
    return {
        "name": _TOOL_NAME,
        "description": "Return structured invoice data extracted from the document.",
        "input_schema": schema,
    }


def _inline_refs(obj: dict, defs: dict) -> None:
    if "$ref" in obj:
        ref_name = obj["$ref"].split("/")[-1]
        obj.clear()
        obj.update(defs.get(ref_name, {}))
    for value in obj.values():
        if isinstance(value, dict):
            _inline_refs(value, defs)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _inline_refs(item, defs)


def _is_retryable(exc: anthropic.APIError) -> bool:
    return isinstance(exc, anthropic.RateLimitError | anthropic.InternalServerError)
