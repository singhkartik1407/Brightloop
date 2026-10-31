from __future__ import annotations

import io
from datetime import date
from decimal import Decimal


def generate_invoice_pdf_content(
    invoice_number: str,
    customer_name: str,
    issue_date: date,
    due_date: date,
    currency: str,
    subtotal: Decimal,
    tax_total: Decimal,
    discount_total: Decimal,
    total: Decimal,
    amount_paid: Decimal,
    amount_due: Decimal,
    status: str,
    lines: list[dict],
) -> bytes:
    """
    Generates a valid standalone PDF 1.4 document containing formatted invoice details
    without requiring third-party binary C libraries.
    """
    text_lines = [
        f"BRIGHTLOOP SUBSCRIPTION MANAGEMENT",
        f"===================================",
        f"INVOICE: {invoice_number}",
        f"Status: {status}",
        f"Customer: {customer_name}",
        f"Issue Date: {issue_date.isoformat()}   Due Date: {due_date.isoformat()}",
        f"Currency: {currency}",
        f"----------------------------------------------------------------",
        f"ITEMS / CHARGES:",
    ]

    for line in lines:
        desc = line.get("description", "Item")
        qty = line.get("quantity", 1)
        price = line.get("unit_price", "0.00")
        ltotal = line.get("line_total", "0.00")
        text_lines.append(f"  * {desc} (Qty: {qty} @ {currency} {price}) -> {currency} {ltotal}")

    text_lines.extend([
        f"----------------------------------------------------------------",
        f"Subtotal:       {currency} {subtotal:.2f}",
        f"Tax Total:      {currency} {tax_total:.2f}",
        f"Discount Total: {currency} {discount_total:.2f}",
        f"Total Amount:   {currency} {total:.2f}",
        f"Amount Paid:    {currency} {amount_paid:.2f}",
        f"Outstanding:    {currency} {amount_due:.2f}",
        f"===================================",
        f"Thank you for your business!",
    ])

    # Construct PDF content stream
    content_stream = ["BT", "/F1 11 Tf", "50 750 Td", "16 TL"]
    for idx, tl in enumerate(text_lines):
        # Escape parenthesis and backslashes for PDF string literal
        escaped = tl.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if idx == 0:
            content_stream.append(f"({escaped}) Tj")
        else:
            content_stream.append(f"T* ({escaped}) Tj")
    content_stream.append("ET")
    stream_data = "\n".join(content_stream).encode("latin-1", errors="replace")

    # Build objects
    objects: list[bytes] = []
    # 1 0 obj: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # 2 0 obj: Pages
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    # 3 0 obj: Page
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    # 4 0 obj: Contents stream
    objects.append(
        b"<< /Length " + str(len(stream_data)).encode("ascii") + b" >>\nstream\n"
        + stream_data
        + b"\nendstream"
    )
    # 5 0 obj: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Assemble PDF with cross-reference table
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{idx} 0 obj\n".encode("ascii"))
        out.write(obj)
        out.write(b"\nendobj\n")

    xref_offset = out.tell()
    out.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    out.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.write(f"{off:010d} 00000 n \n".encode("ascii"))

    out.write(b"trailer\n")
    out.write(f"<< /Size {len(offsets)} /Root 1 0 R >>\n".encode("ascii"))
    out.write(b"startxref\n")
    out.write(f"{xref_offset}\n%%EOF\n".encode("ascii"))

    return out.getvalue()
