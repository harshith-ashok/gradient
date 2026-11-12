"""Turn an uploaded file into plain text. Built as a LangGraph so each step is explicit:

    sniff ─┬─ text ──────┐
           ├─ pdf ───────┤
           ├─ docx ──────┼─► clean
           └─ image(OCR) ┘

PDFs are read directly; any page with (almost) no text layer is rendered and read by the vision
model, which also handles photos of printed or handwritten syllabi.
"""

import io
import re
import zipfile
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.agents.llm import LLM, LLMError

MAX_PDF_PAGES = 60
MAX_TEXT_CHARS = 200_000
MIN_PAGE_TEXT = 25  # a PDF page with less text than this may be a scan (checked before OCR)
BLANK_THRESHOLD = 250  # a rendered page whose darkest pixel is lighter than this is blank
MAX_DOCX_UNCOMPRESSED = 50 * 1024 * 1024

IMAGE_MAGIC = {b"\x89PNG": "png", b"\xff\xd8\xff": "jpg", b"RIFF": "webp"}


class IngestError(Exception):
    """The file cannot be read (unsupported, corrupt, too large, or empty). Safe to show faculty."""


class IngestState(TypedDict, total=False):
    data: bytes
    filename: str
    kind: str
    text: str
    ocr_used: bool
    pages_ocr: int


def detect_kind(data: bytes, filename: str) -> str:
    """Decide by content first, then extension. Never trust the extension alone."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:4] == b"PK\x03\x04":
        if ext == "docx":
            return "docx"
        raise IngestError("Only .docx Word files are supported (not other zip-based formats).")
    for magic in IMAGE_MAGIC:
        if data.startswith(magic):
            return "image"
    if ext in ("txt", "md", "markdown", "text", ""):
        utf16 = data[:2] in (b"\xff\xfe", b"\xfe\xff")  # Windows "Unicode" text files are full of NULs
        if b"\x00" in data[:2000] and not utf16:
            raise IngestError("This file looks binary. Upload a PDF, Word (.docx), image or text file.")
        return "text"
    raise IngestError(f"Unsupported file type '.{ext}'. Upload a PDF, Word (.docx), image, .txt or .md file.")


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeError:
            continue
    return data.decode("utf-8", errors="replace")


def build_ingest_graph(llm: LLM):
    def sniff(state: IngestState) -> IngestState:
        return {"kind": detect_kind(state["data"], state["filename"]), "ocr_used": False, "pages_ocr": 0}

    def read_text(state: IngestState) -> IngestState:
        return {"text": _decode(state["data"])}

    def read_docx(state: IngestState) -> IngestState:
        import docx

        try:
            with zipfile.ZipFile(io.BytesIO(state["data"])) as z:
                if sum(i.file_size for i in z.infolist()) > MAX_DOCX_UNCOMPRESSED:
                    raise IngestError("This Word file is too large once unpacked.")
            d = docx.Document(io.BytesIO(state["data"]))
        except IngestError:
            raise
        except Exception as e:  # noqa: BLE001
            raise IngestError("This Word file could not be opened. Is it corrupt?") from e
        lines = []
        for p in d.paragraphs:
            if not p.text.strip():
                continue
            style = (p.style.name or "") if p.style is not None else ""
            m = re.match(r"Heading (\d)", style)
            lines.append(("#" * int(m.group(1)) + " " if m else "") + p.text)
        for t in d.tables:  # syllabi often put the schedule in a table
            for row in t.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    lines.append(" | ".join(cells))
        return {"text": "\n".join(lines)}

    def read_pdf(state: IngestState) -> IngestState:
        import pypdf
        import pypdfium2 as pdfium

        try:
            reader = pypdf.PdfReader(io.BytesIO(state["data"]))
            if reader.is_encrypted:
                raise IngestError("This PDF is password protected.")
            n = len(reader.pages)
            if n > MAX_PDF_PAGES:
                raise IngestError(f"This PDF has {n} pages; the limit is {MAX_PDF_PAGES}.")
            pages = [(p.extract_text() or "").strip() for p in reader.pages]
        except IngestError:
            raise
        except Exception as e:  # noqa: BLE001
            raise IngestError("This PDF could not be read. Is it corrupt?") from e

        ocr_pages = 0
        if any(len(t) < MIN_PAGE_TEXT for t in pages):
            pdf = pdfium.PdfDocument(state["data"])
            for i, t in enumerate(pages):
                if len(t) >= MIN_PAGE_TEXT:
                    continue
                img = pdf[i].render(scale=2).to_pil().convert("RGB")
                if img.convert("L").getextrema()[0] >= BLANK_THRESHOLD:
                    continue  # a blank page: nothing to read
                png = io.BytesIO()
                img.save(png, format="PNG")
                read = llm.ocr(png.getvalue())
                ocr_pages += 1
                if len(read) > len(t):  # keep the text layer if OCR found no more than it did
                    pages[i] = read
        return {"text": "\n\n".join(pages), "ocr_used": ocr_pages > 0, "pages_ocr": ocr_pages}

    def read_image(state: IngestState) -> IngestState:
        from PIL import Image

        try:
            img = Image.open(io.BytesIO(state["data"]))
            img.load()
            img = img.convert("RGB")
            if max(img.size) > 3000:  # keep the request a sensible size for the vision model
                img.thumbnail((3000, 3000))
        except Exception as e:  # noqa: BLE001
            raise IngestError("This image could not be read.") from e
        png = io.BytesIO()
        img.save(png, format="PNG")
        return {"text": llm.ocr(png.getvalue()), "ocr_used": True, "pages_ocr": 1}

    def clean(state: IngestState) -> IngestState:
        text = state["text"].replace("\x00", "")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if len(text) < 20:
            raise IngestError("No readable text was found in this file.")
        return {"text": text[:MAX_TEXT_CHARS]}

    g = StateGraph(IngestState)
    g.add_node("sniff", sniff)
    g.add_node("text", read_text)
    g.add_node("docx", read_docx)
    g.add_node("pdf", read_pdf)
    g.add_node("image", read_image)
    g.add_node("clean", clean)
    g.set_entry_point("sniff")
    g.add_conditional_edges("sniff", lambda s: s["kind"], {k: k for k in ("text", "docx", "pdf", "image")})
    for k in ("text", "docx", "pdf", "image"):
        g.add_edge(k, "clean")
    g.add_edge("clean", END)
    return g.compile()


def extract_text(llm: LLM, data: bytes, filename: str) -> dict:
    """Returns {text, ocr_used, pages_ocr}. Raises IngestError with a message safe to show."""
    try:
        out = build_ingest_graph(llm).invoke({"data": data, "filename": filename})
    except LLMError as e:
        raise IngestError(f"Reading scanned pages failed: {e}") from e
    return {"text": out["text"], "ocr_used": out.get("ocr_used", False), "pages_ocr": out.get("pages_ocr", 0)}
