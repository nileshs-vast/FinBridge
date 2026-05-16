"""Generate sample invoice PDFs from the FixtureProvider seed JSONs.

Each PDF is named to match its seed JSON stem so uploading it through the
FinBridge UI lands on the rich fixture extraction (see
backend/app/extraction/fixture.py).

Run:
    python3 scripts/generate_sample_invoices.py
"""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SEEDS_DIR = ROOT / "backend" / "seeds" / "extractions"
OUT_DIR = ROOT / "sample_invoices"

CUSTOMER_NAME = "Acme Manufacturing Pvt Ltd"
CUSTOMER_ADDRESS = "Plot 21, MIDC Industrial Estate, Pune 411019, Maharashtra"


def fmt_money(value: float | None, currency: str = "INR") -> str:
    if value is None:
        return "—"
    return f"{currency} {value:,.2f}"


def fmt_qty(value: float | None) -> str:
    if value is None:
        return "—"
    if float(value).is_integer():
        return f"{int(value)}"
    return f"{value:,.2f}"


def build_pdf(seed_path: Path, out_path: Path) -> None:
    data = json.loads(seed_path.read_text())
    is_salary = "salary" in seed_path.stem.lower()

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=data.get("invoice_no") or seed_path.stem,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=20, leading=24, textColor=colors.HexColor("#0f172a"))
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], fontSize=11, leading=14, textColor=colors.HexColor("#334155"))
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"))

    story: list = []

    title = "Salary Register" if is_salary else "Tax Invoice"
    story.append(Paragraph(f"<b>{data['vendor']}</b>", h1))
    if data.get("vendor_address"):
        story.append(Paragraph(data["vendor_address"], small))
    if data.get("vendor_gstin"):
        story.append(Paragraph(f"GSTIN: <b>{data['vendor_gstin']}</b>", small))
    story.append(Spacer(1, 6 * mm))

    header_rows = [
        [Paragraph(f"<b>{title}</b>", h3), Paragraph(f"<b>Invoice No.</b> {data.get('invoice_no', '—')}", body)],
        ["", Paragraph(f"<b>Invoice Date:</b> {data.get('invoice_date', '—')}", body)],
    ]
    if data.get("due_date"):
        header_rows.append(["", Paragraph(f"<b>Due Date:</b> {data['due_date']}", body)])
    if data.get("place_of_supply"):
        header_rows.append(["", Paragraph(f"<b>Place of Supply:</b> {data['place_of_supply']}", body)])

    header_table = Table(header_rows, colWidths=[None, 75 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    bill_to = [
        Paragraph("<b>Bill To</b>", h3),
        Paragraph(f"<b>{CUSTOMER_NAME}</b>", body),
        Paragraph(CUSTOMER_ADDRESS, body),
    ]
    if data.get("customer_gstin"):
        bill_to.append(Paragraph(f"GSTIN: <b>{data['customer_gstin']}</b>", body))
    for elt in bill_to:
        story.append(elt)
    story.append(Spacer(1, 6 * mm))

    if is_salary:
        line_header = ["#", "Description", "Headcount", "Avg / Employee", "Amount"]
    else:
        line_header = ["#", "Description", "HSN/SAC", "Qty", "Rate", "Amount"]

    line_rows = [line_header]
    for idx, item in enumerate(data.get("line_items", []), start=1):
        if is_salary:
            line_rows.append(
                [
                    str(idx),
                    item.get("description", ""),
                    fmt_qty(item.get("quantity")),
                    fmt_money(item.get("unit_price"), data.get("currency", "INR")),
                    fmt_money(item.get("amount"), data.get("currency", "INR")),
                ]
            )
        else:
            line_rows.append(
                [
                    str(idx),
                    item.get("description", ""),
                    item.get("hsn_sac") or "—",
                    fmt_qty(item.get("quantity")),
                    fmt_money(item.get("unit_price"), data.get("currency", "INR")),
                    fmt_money(item.get("amount"), data.get("currency", "INR")),
                ]
            )

    if is_salary:
        line_table = Table(line_rows, colWidths=[10 * mm, 80 * mm, 25 * mm, 35 * mm, 35 * mm])
    else:
        line_table = Table(line_rows, colWidths=[10 * mm, 60 * mm, 20 * mm, 18 * mm, 30 * mm, 35 * mm])

    line_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (-3, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(line_table)
    story.append(Spacer(1, 6 * mm))

    currency = data.get("currency", "INR")
    totals_rows = [["Subtotal", fmt_money(data.get("subtotal"), currency)]]
    if data.get("cgst") is not None:
        totals_rows.append(["CGST", fmt_money(data.get("cgst"), currency)])
    if data.get("sgst") is not None:
        totals_rows.append(["SGST", fmt_money(data.get("sgst"), currency)])
    if data.get("igst") is not None:
        totals_rows.append(["IGST", fmt_money(data.get("igst"), currency)])
    if not is_salary and data.get("tax_amount") is not None:
        totals_rows.append(["Total Tax", fmt_money(data.get("tax_amount"), currency)])
    totals_rows.append(["Total", fmt_money(data.get("total"), currency)])

    totals_table = Table(totals_rows, colWidths=[40 * mm, 45 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.6, colors.HexColor("#0f172a")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#0f172a")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 8 * mm))

    if data.get("reverse_charge"):
        story.append(Paragraph("<b>Tax payable on reverse charge:</b> Yes", body))
        story.append(Spacer(1, 2 * mm))

    if data.get("notes"):
        story.append(Paragraph(f"<b>Notes:</b> {data['notes']}", small))
        story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "This is a system-generated document for demonstration purposes only. "
            "All figures, GSTINs, and entity names are illustrative.",
            small,
        )
    )

    doc.build(story)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seeds = sorted(SEEDS_DIR.glob("*.json"))
    if not seeds:
        raise SystemExit(f"No seed JSONs found in {SEEDS_DIR}")

    for seed in seeds:
        out_pdf = OUT_DIR / f"{seed.stem}.pdf"
        build_pdf(seed, out_pdf)
        print(f"  wrote {out_pdf.relative_to(ROOT)}")

    print(f"\nDone — {len(seeds)} files in {OUT_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
