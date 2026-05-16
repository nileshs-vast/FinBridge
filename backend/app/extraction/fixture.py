from __future__ import annotations

import hashlib
from pathlib import Path

from .schema import ExtractedInvoice, LineItem


class FixtureProvider:
    name = "fixture"

    def __init__(self, seeds_dir: str = "seeds/extractions") -> None:
        self._seeds_dir = Path(seeds_dir)

    async def extract(self, file_path: Path, mime_type: str) -> ExtractedInvoice:
        file_bytes = file_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Files are stored as "{uuid4()}_{original_name}" — strip the 37-char
        # UUID+underscore prefix to recover the original stem for seed lookup.
        stem = file_path.stem
        original_stem = stem[37:] if len(stem) > 37 and stem[36] == "_" else stem

        for candidate in (
            self._seeds_dir / f"{file_hash}.json",
            self._seeds_dir / f"{original_stem}.json",
        ):
            if candidate.exists():
                return ExtractedInvoice.model_validate_json(candidate.read_text())

        return _generic_mock()


def _generic_mock() -> ExtractedInvoice:
    return ExtractedInvoice(
        vendor="Sample Vendor Pvt Ltd",
        vendor_gstin="27AABCU9603R1ZP",
        invoice_no="INV-2024-001",
        total=10000.0,
        subtotal=8474.58,
        tax_amount=1525.42,
        cgst=762.71,
        sgst=762.71,
        currency="INR",
        line_items=[
            LineItem(
                description="Professional Services",
                quantity=1.0,
                unit_price=8474.58,
                amount=8474.58,
                hsn_sac="9983",
            )
        ],
        suggested_direction="purchase",
        confidence={"vendor": 0.5, "total": 0.5, "invoice_no": 0.5},
        notes="Fixture fallback — no matching seed found for this file.",
    )
