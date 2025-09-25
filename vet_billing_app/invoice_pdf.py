
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_RIGHT
from PIL import Image

import os
from datetime import datetime

PAGE_W, PAGE_H = A4

def draw_text(c, x, y, text, size=10, bold=False, align="left"):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    if align == "right":
        c.drawRightString(x, y, text)
    else:
        c.drawString(x, y, text)

def draw_box(c, x, y, w, h, stroke=1):
    c.setLineWidth(stroke)
    c.rect(x, y, w, h)

def mmx(val): return val * mm

def create_invoice_pdf(path, data, items, logo_path=None):
    c = canvas.Canvas(path, pagesize=A4)
    margin = mmx(10)
    y = PAGE_H - margin

    # Header with logo + clinic info
    if logo_path and os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, margin, y - mmx(18), width=mmx(28), height=mmx(28), preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    draw_text(c, margin + mmx(35), y - mmx(10), "VETS ONE", size=18, bold=True)
    draw_text(c, margin + mmx(35), y - mmx(18), "ANIMAL HOSPITAL", size=10)

    clinic_addr = "No.321/B, Divulpitiya, Boralesgamuwa\nTel : +94 77 8198 882 | +94 704130 333"
    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleN.fontName = "Helvetica"
    styleN.fontSize = 9
    from reportlab.platypus import Frame
    f = Frame(margin + mmx(35), y - mmx(38), mmx(80), mmx(22), showBoundary=0)
    f.addFromList([Paragraph(clinic_addr.replace("\n", "<br/>"), styleN)], c)

    # Receipt info box (right)
    box_w = mmx(80)
    box_h = mmx(36)
    x_box = PAGE_W - margin - box_w
    y_box = y - mmx(5) - box_h
    draw_box(c, x_box, y_box, box_w, box_h)
    draw_text(c, x_box + mmx(4), y_box + box_h - mmx(8), "Receipt Number :", bold=True)
    draw_text(c, x_box + mmx(45), y_box + box_h - mmx(8), data["receipt_no"] or "—")
    draw_text(c, x_box + mmx(4), y_box + box_h - mmx(16), "Date :", bold=True)
    draw_text(c, x_box + mmx(45), y_box + box_h - mmx(16), data["date"])
    draw_text(c, x_box + mmx(4), y_box + box_h - mmx(24), "Payment Method :", bold=True)
    draw_text(c, x_box + mmx(45), y_box + box_h - mmx(24), data["payment_method"] or "—")

    # Customer info boxes
    top_y = y_box - mmx(6)
    left_w = PAGE_W - 2*margin
    draw_box(c, margin, top_y - mmx(28), left_w, mmx(28))
    # Left half: customer
    draw_text(c, margin + mmx(4), top_y - mmx(8), "Customer Name :", bold=True)
    draw_text(c, margin + mmx(40), top_y - mmx(8), data["customer_name"] or "—")
    draw_text(c, margin + mmx(4), top_y - mmx(16), "Address :", bold=True)
    draw_text(c, margin + mmx(40), top_y - mmx(16), data["address"] or "—")
    # Right half: contact
    draw_text(c, margin + mmx(120), top_y - mmx(8), "Tele :", bold=True)
    draw_text(c, margin + mmx(140), top_y - mmx(8), data["telephone"] or "—")
    draw_text(c, margin + mmx(120), top_y - mmx(16), "E-mail :", bold=True)
    draw_text(c, margin + mmx(140), top_y - mmx(16), data["email"] or "—")

    # Table header
    table_top = top_y - mmx(34)
    table_h = mmx(160)
    draw_box(c, margin, table_top - table_h, left_w, table_h)

    cols = [
        ("Item #", mmx(22)),
        ("Product Description", mmx(95)),
        ("Qty", mmx(15)),
        ("Price Per Unit", mmx(28)),
        ("Cost", mmx(25)),
    ]
    x = margin
    for label, width in cols:
        draw_box(c, x, table_top - mmx(8), width, mmx(8))
        draw_text(c, x + mmx(3), table_top - mmx(6), label, bold=True, size=10)
        x += width

    # Lines
    row_h = mmx(10)
    max_rows = int((table_h - mmx(8)) // row_h)
    y_row = table_top - mmx(8) - row_h
    for i in range(max_rows):
        # Verticals drawn via column boxes below; draw row lines
        c.line(margin, y_row, margin + left_w, y_row)
        y_row -= row_h

    # Column verticals
    x = margin
    for _, width in cols:
        c.line(x, table_top - table_h, x, table_top)
        x += width
    c.line(x, table_top - table_h, x, table_top)

    # Fill rows
    x_positions = [margin]
    s = 0
    for _, width in cols:
        s += width
        x_positions.append(margin + s)

    y_cursor = table_top - mmx(8) - row_h + mmx(3)
    for idx, it in enumerate(items[:max_rows]):
        c.setFont("Helvetica", 9)
        c.drawString(x_positions[0] + mmx(3), y_cursor, str(it.get("item_no","")))
        c.drawString(x_positions[1] + mmx(3), y_cursor, it.get("description",""))
        c.drawRightString(x_positions[2+0] - mmx(2), y_cursor, f"{it.get('qty',0)}")
        c.drawRightString(x_positions[3+0] - mmx(2), y_cursor, f"{it.get('unit_price',0):.2f}")
        c.drawRightString(x_positions[4+0] - mmx(2), y_cursor, f"{it.get('line_total',0):.2f}")
        y_cursor -= row_h

    # Comments box + Total
    comments_h = mmx(35)
    draw_box(c, margin, table_top - table_h - mmx(4) - comments_h, mmx(120), comments_h)
    draw_text(c, margin + mmx(3), table_top - table_h - mmx(4) - mmx(6), "Comments :", bold=True)

    # Total box
    total_w = mmx(40)
    total_x = PAGE_W - margin - total_w
    total_y = table_top - table_h - mmx(4) - comments_h
    draw_box(c, total_x - mmx(20), total_y, total_w, comments_h)
    draw_text(c, total_x - mmx(18), total_y + comments_h - mmx(8), "Total", bold=True)
    draw_text(c, total_x + mmx(16), total_y + comments_h - mmx(8), f"{data['total']:.2f}", bold=True, align="right")

    # Signature line
    c.line(PAGE_W - margin - mmx(70), margin + mmx(18), PAGE_W - margin, margin + mmx(18))
    draw_text(c, PAGE_W - margin - mmx(30), margin + mmx(12), "Signature", size=9)

    c.showPage()
    c.save()
