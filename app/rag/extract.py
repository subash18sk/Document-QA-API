"""
Step 1 of indexing: turn an uploaded file into clean text, page by page.

Page numbers are kept so every answer can cite where it came from ("p. 4").
"""
import io
import os
import re
from dataclasses import dataclass

from pypdf import PdfReader
from pypdf.errors import PdfReadError

SUPPORTED_EXTENSIONS = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}


class ExtractionError(ValueError):
    """The file can't be turned into text (bad format, encrypted, image-only, ...)."""


class UnsupportedFileType(ExtractionError):
    pass


@dataclass
class Page:
    number: int      # 1-based
    text: str


def _is_heading(line: str) -> bool:
    """Short line with no closing punctuation, e.g. '2. Leave Policy' or '## Benefits'."""
    words = line.split()
    return 0 < len(words) <= 8 and not line.endswith((".", ":", ";", ",", "?", "!"))


def _clean(text: str) -> str:
    text = text.replace("­", "")                    # soft hyphens
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)          # words split across lines: "employ-\nees"
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    lines = [ln.strip().lstrip("#").strip() for ln in text.split("\n")]
    # End headings with a colon: they become their own "sentence", never glued onto the next one,
    # and the answerer can recognise (and skip) them as answers.
    lines = [ln + ":" if _is_heading(ln) else ln for ln in lines if ln]
    return "\n".join(lines).strip()


def _pdf_pages(data: bytes) -> list[Page]:
    if not data.startswith(b"%PDF"):
        raise ExtractionError("The file does not look like a valid PDF.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("The PDF is password-protected.")
        return [Page(i + 1, _clean(p.extract_text() or "")) for i, p in enumerate(reader.pages)]
    except PdfReadError as exc:
        raise ExtractionError(f"The PDF could not be read: {exc}") from exc


def _text_pages(data: bytes) -> list[Page]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExtractionError("Text files must be UTF-8 encoded.") from exc
    # A form-feed character is the conventional page break in plain text.
    return [Page(i + 1, _clean(part)) for i, part in enumerate(text.split("\f"))]


def extract_pages(filename: str, data: bytes) -> list[Page]:
    ext = os.path.splitext(filename.lower())[1]
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileType(f"Unsupported file type '{ext or 'none'}'. Upload a PDF, .txt or .md file.")
    pages = _pdf_pages(data) if ext == ".pdf" else _text_pages(data)
    if not any(p.text for p in pages):
        raise ExtractionError(
            "No text could be extracted. Scanned or image-only PDFs need OCR, which this API doesn't do yet."
        )
    return pages
