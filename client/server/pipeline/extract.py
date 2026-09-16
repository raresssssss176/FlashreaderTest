"""
server/pipeline/extract.py

Turns an uploaded .pdf or .txt into clean prose the analyzer can chew on.
PDFs in particular need work: hyphenated line breaks, hard-wrapped lines
and repeated page furniture all confuse sentence splitting.
"""

import io
import re
from typing import Tuple

SUPPORTED = (".pdf", ".txt", ".text", ".md")


class ExtractionError(Exception):
    pass


def extract(filename: str, data: bytes) -> Tuple[str, str]:
    """Returns (text, source_kind). Raises ExtractionError on failure."""
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return clean_text(_from_pdf(data)), "pdf"
    if name.endswith(SUPPORTED):
        return clean_text(_from_txt(data)), "txt"
    raise ExtractionError(
        f"Format nesuportat: {filename}. Accept .pdf, .txt, .md")


def _from_txt(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1250", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


def _from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError("pypdf nu este instalat: pip install pypdf") from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"PDF invalid: {exc}") from exc

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")

    text = "\n\n".join(pages)
    if len(text.strip()) < 40:
        raise ExtractionError(
            "PDF-ul nu contine text (probabil e scanat). "
            "Ruleaza OCR pe el mai intai, sau incarca un .txt.")
    return _drop_repeated_lines(text)


def _drop_repeated_lines(text: str) -> str:
    """
    Headers, footers and page numbers repeat on almost every page. Any
    short line appearing on more than a third of the pages is furniture.
    """
    pages = text.split("\n\n")
    if len(pages) < 6:
        return text

    counts = {}
    for page in pages:
        for line in set(page.strip().splitlines()):
            stripped = line.strip()
            if 0 < len(stripped) <= 70:
                counts[stripped] = counts.get(stripped, 0) + 1

    threshold = max(3, len(pages) // 3)
    junk = {line for line, n in counts.items() if n >= threshold}
    if not junk:
        return text

    kept = []
    for page in pages:
        lines = [ln for ln in page.splitlines()
                 if ln.strip() not in junk and not re.fullmatch(r"\s*\d{1,4}\s*", ln)]
        kept.append("\n".join(lines))
    return "\n\n".join(kept)


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Curly quotes and dashes -> plain, so tokenisation is predictable
    for bad, good in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'),
                      ("\u201d", '"'), ("\u2014", " - "), ("\u2013", "-"),
                      ("\u00a0", " "), ("\ufb01", "fi"), ("\ufb02", "fl")):
        text = text.replace(bad, good)

    # Re-join words split across a line break: "compre-\nhension"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    # Mark real paragraph breaks before collapsing single newlines
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"(?<![\n.!?:;\"'])\n(?!\n)", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))
