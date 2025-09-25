from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet

PAGE_W, PAGE_H = A4

def draw_text(c, x, y, text, size=10, bold=False, align="left"):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    (c.drawRightString if align == "right" else c.drawString)(x, y, text)

def draw_box(c, x, y, w, h, stroke=1):
    c.setLineWidth(stroke)
    c.rect(x, y, w, h)

def mmx(v):  # mm → points
    return v * mm

def create_invoice_pdf(path, data, items, logo_path=None):
    c = canvas.Canvas(path, pagesize=A4)
    margin = mmx(10)
    y = PAGE_H - margin

    # Header (logo + clinic info)
    if logo_path:
        try:
            c.drawImage(logo_path, margin, y - mmx(18),
                        width=mmx(28), height=mmx(28), mask='auto')
        except Exception:
            pass
    draw_text(c, margin + mmx(35), y - mmx(10), "VETS ONE", 18, True)
    draw_text(c, margin + mmx(35), y - mmx(18), "ANIMAL HOSPITAL", 10)

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]; styleN.fontSize = 9
    addr = "No.321/B, Divulpitiya, Boralesgamuwa<br/>Tel : +94 77 8198 882 | +94 704130 333"
    Frame(margin + mmx(35), y - mmx(38), mmx(80), mmx(22)).addFromList([Paragraph(addr, styleN)], c)

    # Receipt box (right)
    box_w, box_h = mmx(80), mmx(36)
    x_box = PAGE_W - margin - box_w
    y_box = y - mmx(5) - box_h
    draw_box(c, x_box, y_box, box_w, box_h)
    draw_text(c, x_box + mmx(4), y_box + box_h - mmx(8), "Receipt Number :", bold=True)
    draw_text(c, x_box + mmx(45), y_box + box_h - mmx(8), data.get("receipt_no", "") or "—")
    draw_text(c, x_box + mmx(4), y_box + box_h - mmx(16), "Date :", bold=True)
    draw_text(c, x_box + mmx(45), y_box + box_h - mmx(16), data.get("date", "") or "—")
    draw_text(c, x_box + mmx(4), y_box + box_h - mmx(24), "Payment Method :", bold=True)
    draw_text(c, x_box + mmx(45), y_box + box_h - mmx(24), data.get("payment_method", "") or "—")

    # Customer/contact box
    top_y = y_box - mmx(6)
    left_w = PAGE_W - 2 * margin
    draw_box(c, margin, top_y - mmx(28), left_w, mmx(28))
    draw_text(c, margin + mmx(4),  top_y - mmx(8),  "Customer Name :", bold=True)
    draw_text(c, margin + mmx(40), top_y - mmx(8),  data.get("customer_name", "") or "—")
    draw_text(c, margin + mmx(4),  top_y - mmx(16), "Address :",       bold=True)
    draw_text(c, margin + mmx(40), top_y - mmx(16), data.get("address", "") or "—")
    draw_text(c, margin + mmx(120), top_y - mmx(8), "Tele :", bold=True)
    draw_text(c, margin + mmx(140), top_y - mmx(8), data.get("telephone", "") or "—")
    draw_text(c, margin + mmx(120), top_y - mmx(16), "E-mail :", bold=True)
    draw_text(c, margin + mmx(140), top_y - mmx(16), data.get("email", "") or "—")

    # Table geometry
    table_top = top_y - mmx(34)
    table_h   = mmx(160)

    # Column widths (mm) converted to points
    cols = [
        ("Item #",           mmx(22)),
        ("Product Description", mmx(95)),
        ("Qty",              mmx(15)),
        ("Price Per Unit",   mmx(28)),
        ("Cost",             mmx(25)),
    ]
    # Compute left edges for each column and the final right edge
    col_lefts = [margin]
    for _, w in cols:
        col_lefts.append(col_lefts[-1] + w)  # lefts[i+1] == right edge of col i

    # Outer table and header cells
    draw_box(c, margin, table_top - table_h, col_lefts[-1] - margin, table_h)

    header_h = mmx(8)
    for i, (label, w) in enumerate(cols):
        draw_box(c, col_lefts[i], table_top - header_h, w, header_h)
        draw_text(c, col_lefts[i] + mmx(3), table_top - mmx(6), label, bold=True, size=10)

    # Row lines
    row_h = mmx(10)
    max_rows = int((table_h - header_h) // row_h)
    y_row = table_top - header_h - row_h
    for _ in range(max_rows):
        c.line(margin, y_row, col_lefts[-1], y_row)
        y_row -= row_h

    # Vertical lines
    for x in col_lefts:
        c.line(x, table_top - table_h, x, table_top)

    # Fill rows (correct alignment per column)
    pad = mmx(3)
    y_cursor = table_top - header_h - row_h + mmx(3)
    for it in items[:max_rows]:
        c.setFont("Helvetica", 9)
        # left edges for item# and description
        c.drawString(col_lefts[0] + pad, y_cursor, str(it.get("item_no", "")))
        c.drawString(col_lefts[1] + pad, y_cursor, it.get("description", ""))
        # right edges for numeric columns -> use right edge of the SAME column: lefts[i+1]
        c.drawRightString(col_lefts[2 + 1] - pad, y_cursor, f"{it.get('qty', 0):g}")
        c.drawRightString(col_lefts[3 + 1] - pad, y_cursor, f"{it.get('unit_price', 0):.2f}")
        c.drawRightString(col_lefts[4 + 1] - pad, y_cursor, f"{it.get('line_total', 0):.2f}")
        y_cursor -= row_h

    # Comments + Total
    comments_h = mmx(35)
    draw_box(c, margin, table_top - table_h - mmx(4) - comments_h, mmx(120), comments_h)
    draw_text(c, margin + mmx(3), table_top - table_h - mmx(4) - mmx(6), "Comments :", bold=True)

    total_w = mmx(40)
    total_x = PAGE_W - margin - total_w
    total_y = table_top - table_h - mmx(4) - comments_h
    draw_box(c, total_x - mmx(20), total_y, total_w, comments_h)
    draw_text(c, total_x - mmx(18), total_y + comments_h - mmx(8), "Total", bold=True)
    draw_text(c, total_x + mmx(16), total_y + comments_h - mmx(8), f"{data.get('total', 0):.2f}", bold=True, align="right")

    # Signature
    c.line(PAGE_W - margin - mmx(70), margin + mmx(18), PAGE_W - margin, margin + mmx(18))
    draw_text(c, PAGE_W - margin - mmx(30), margin + mmx(12), "Signature", size=9)

    c.showPage()
    c.save()
