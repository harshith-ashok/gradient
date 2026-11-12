import io

import pytest

from app.agents.ingest import IngestError, detect_kind, extract_text
from app.agents.llm import FakeLLM, LLMError
from tests.files import make_docx, make_pdf, make_png, make_scanned_pdf


def ingest(data: bytes, name: str, llm: FakeLLM | None = None):
    return extract_text(llm or FakeLLM(), data, name)


# ----------------------------------------------------------------- sniffing


@pytest.mark.parametrize(("data", "name", "kind"), [
    (b"%PDF-1.7 ...", "x.pdf", "pdf"),
    (b"%PDF-1.7 ...", "misnamed.txt", "pdf"),  # content wins over extension
    (b"\x89PNG\r\n", "scan.png", "image"),
    (b"\xff\xd8\xff\xe0", "photo.jpg", "image"),
    (b"hello", "notes.md", "text"),
    (b"hello", "notes", "text"),
])
def test_detect_kind(data, name, kind):
    assert detect_kind(data, name) == kind


def test_docx_is_detected_by_zip_signature_and_extension():
    assert detect_kind(make_docx(), "s.docx") == "docx"


@pytest.mark.parametrize(("data", "name"), [
    (b"PK\x03\x04junk", "archive.zip"),  # not a Word file
    (b"MZ\x90\x00", "virus.exe"),
    (b"\x00\x01\x02binary" * 50, "data.txt"),  # NUL bytes in a "text" file
])
def test_unsupported_files_are_rejected(data, name):
    with pytest.raises(IngestError):
        detect_kind(data, name)


# --------------------------------------------------------------- text files


def test_plain_text_and_encodings():
    assert "Topic one" in ingest(b"Topic one\nTopic two is next here", "a.txt")["text"]
    latin = "Café résumé — week one syllabus".encode("latin-1", errors="replace")
    assert "week one" in ingest(latin, "a.txt")["text"]
    assert "naïve topic" in ingest("﻿naïve topic list goes here".encode(), "a.md")["text"]


def test_whitespace_is_normalised():
    out = ingest(b"Line one   \n\n\n\n\nLine two continues here", "a.txt")["text"]
    assert out == "Line one\n\nLine two continues here"


def test_utf16_text_files_are_accepted():
    """Windows Notepad's "Unicode" text files are UTF-16 with a byte-order mark and many NULs."""
    data = "Week 1: Nuclear physics basics\nWeek 2: Quantum mechanics".encode("utf-16")
    assert "Quantum mechanics" in ingest(data, "notes.txt")["text"]


@pytest.mark.parametrize("data", [b"", b"   \n  ", b"tiny"])
def test_empty_or_tiny_files_are_rejected(data):
    with pytest.raises(IngestError, match="No readable text"):
        ingest(data, "a.txt")


def test_text_is_capped():
    out = ingest(("word " * 100).encode() * 1000, "big.txt")["text"]
    assert len(out) == 200_000


# ---------------------------------------------------------------------- PDF


def test_text_pdf_is_read_without_ocr():
    llm = FakeLLM()
    pdf = make_pdf(["Week 1: Sorting algorithms and their analysis", "Week 2: Graph search methods"])
    out = ingest(pdf, "s.pdf", llm)
    assert "Sorting algorithms" in out["text"] and "Graph search" in out["text"]
    assert out["ocr_used"] is False and out["pages_ocr"] == 0
    assert not any(c["schema"] == "ocr" for c in llm.calls)


def test_scanned_pdf_goes_through_the_vision_model():
    llm = FakeLLM()
    llm.ocr_texts = ["1. Arrays and lists\n- indexing", "2. Trees and graphs\n- traversal"]
    out = ingest(make_scanned_pdf(["page one", "page two"]), "scan.pdf", llm)
    assert out["ocr_used"] is True and out["pages_ocr"] == 2
    assert "Arrays and lists" in out["text"] and "Trees and graphs" in out["text"]
    assert out["text"].index("Arrays") < out["text"].index("Trees")  # page order kept


def test_mixed_pdf_only_ocrs_the_pages_that_need_it():
    from pypdf import PdfWriter

    text_pdf = make_pdf(["Week 1: Introduction to the course and its main ideas"])
    scan_pdf = make_scanned_pdf(["handwritten page"])
    w = PdfWriter()
    for blob in (text_pdf, scan_pdf):
        import pypdf

        for page in pypdf.PdfReader(io.BytesIO(blob)).pages:
            w.add_page(page)
    buf = io.BytesIO()
    w.write(buf)
    llm = FakeLLM()
    llm.ocr_texts = ["Week 2: Handwritten notes about recursion"]
    out = ingest(buf.getvalue(), "mixed.pdf", llm)
    assert out["pages_ocr"] == 1 and out["ocr_used"] is True
    assert "Introduction to the course" in out["text"] and "recursion" in out["text"]


def test_blank_pages_are_skipped_without_calling_the_model():
    llm = FakeLLM()
    out = ingest(make_pdf(["Week 1: Introduction to the course and its main ideas", "", "Week 3: Recursion in depth"]),
                 "gaps.pdf", llm)
    assert out["ocr_used"] is False and not any(c["schema"] == "ocr" for c in llm.calls)
    assert "Recursion" in out["text"]


def test_short_text_layer_is_kept_when_ocr_finds_no_more():
    llm = FakeLLM()
    llm.ocr_texts = ["??"]  # OCR reads less than the PDF already contains
    out = ingest(make_pdf(["Week 1: Introduction to the course and its main ideas", "Hello"]), "short.pdf", llm)
    assert "Hello" in out["text"] and "??" not in out["text"]


def test_corrupt_pdf():
    with pytest.raises(IngestError, match="could not be read"):
        ingest(b"%PDF-1.4 this is not really a pdf", "bad.pdf")


def test_password_protected_pdf():
    import pypdf

    r = pypdf.PdfReader(io.BytesIO(make_pdf(["secret syllabus text that is long enough"])))
    w = pypdf.PdfWriter()
    w.append(r)
    w.encrypt("hunter2")
    buf = io.BytesIO()
    w.write(buf)
    with pytest.raises(IngestError, match="password"):
        ingest(buf.getvalue(), "locked.pdf")


def test_page_limit():
    with pytest.raises(IngestError, match="limit is 60"):
        ingest(make_pdf([f"Page {i} has some text on it for the test" for i in range(61)]), "long.pdf")


def test_ocr_failure_is_reported_not_swallowed():
    class Broken(FakeLLM):
        def ocr(self, image_png):
            raise LLMError("vision model offline")

    with pytest.raises(IngestError, match="vision model offline"):
        ingest(make_scanned_pdf(["x"]), "scan.pdf", Broken())


def test_pdf_where_ocr_finds_nothing_is_rejected():
    llm = FakeLLM()
    llm.ocr_texts = [""]
    with pytest.raises(IngestError, match="No readable text"):
        ingest(make_scanned_pdf(["blank"]), "scan.pdf", llm)


# -------------------------------------------------------------------- images


def test_image_uses_ocr():
    llm = FakeLLM()
    llm.ocr_texts = ["Week 1: Pointers\nWeek 2: Memory"]
    out = ingest(make_png(), "photo.png", llm)
    assert out["ocr_used"] is True and "Pointers" in out["text"]
    assert [c for c in llm.calls if c["schema"] == "ocr"][0]["bytes"] > 100


def test_corrupt_image():
    with pytest.raises(IngestError, match="image could not be read"):
        ingest(b"\x89PNG\r\n\x1a\n" + b"garbage", "x.png")


def test_huge_image_is_downscaled_before_ocr():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (6000, 4000), "white").save(buf, format="PNG")
    llm = FakeLLM()
    ingest(buf.getvalue(), "big.png", llm)
    sent = [c for c in llm.calls if c["schema"] == "ocr"][0]["bytes"]
    assert sent < len(buf.getvalue()) * 5  # a normal-sized request, not a 6000px one


# ---------------------------------------------------------------------- DOCX


def test_docx_headings_paragraphs_and_tables():
    text = ingest(make_docx(), "s.docx")["text"]
    assert "# CS 330: Databases" in text and "## Relational model" in text and "## SQL" in text
    assert "Queries, joins and aggregation." in text
    assert "Week 2 | SQL basics" in text  # the schedule table is not lost


def test_corrupt_docx():
    with pytest.raises(IngestError, match="could not be opened"):
        ingest(b"PK\x03\x04 not really a word file at all", "x.docx")
