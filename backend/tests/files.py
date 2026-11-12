"""Build real PDF / DOCX / image files for tests."""

import io

from PIL import Image, ImageDraw, ImageFont


def make_pdf(pages: list[str]) -> bytes:
    """A PDF with a real text layer, one string per page."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    for text in pages:
        y = 800
        for line in text.splitlines():
            c.drawString(60, y, line)
            y -= 18
        c.showPage()
    c.save()
    return buf.getvalue()


def page_image(text: str, size=(900, 600)) -> Image.Image:
    img = Image.new("RGB", size, "white")
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=28)
    y = 40
    for line in text.splitlines():
        d.text((40, y), line, fill="black", font=font)
        y += 44
    return img


def make_scanned_pdf(texts: list[str]) -> bytes:
    """A PDF that is only pictures of pages (no text layer), like a scan."""
    imgs = [page_image(t) for t in texts]
    buf = io.BytesIO()
    imgs[0].save(buf, format="PDF", save_all=True, append_images=imgs[1:])
    return buf.getvalue()


def make_png(text: str = "Week 1: Introduction") -> bytes:
    buf = io.BytesIO()
    page_image(text).save(buf, format="PNG")
    return buf.getvalue()


def make_docx() -> bytes:
    import docx

    d = docx.Document()
    d.add_heading("CS 330: Databases", level=1)
    d.add_heading("Relational model", level=2)
    d.add_paragraph("Tables, keys and relational algebra.")
    d.add_heading("SQL", level=2)
    d.add_paragraph("Queries, joins and aggregation.")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Week 1", "Relational model"
    t.cell(1, 0).text, t.cell(1, 1).text = "Week 2", "SQL basics"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


SYLLABUS_TEXT = """CS 330: Databases

# Relational model
Tables, keys, relational algebra and normal forms.

# SQL
Queries, joins, aggregation and subqueries.

# Transactions
ACID properties, isolation levels and locking.
"""
