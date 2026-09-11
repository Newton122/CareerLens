from __future__ import annotations

import logging
from pathlib import Path

import fitz

logger = logging.getLogger(__name__)


class TextExtractionError(Exception):
    """A document could not be read.

    Raised instead of letting library-specific exceptions escape: PyMuPDF
    errors carry the absolute server path of the temporary file, and an
    unhandled one becomes a 500 for what is really a bad-input problem the
    user can act on.
    """


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract plain text from a PDF file."""
    pdf_path = Path(file_path)
    text_chunks: list[str] = []

    try:
        with fitz.open(pdf_path) as pdf:
            if pdf.needs_pass:
                raise TextExtractionError(
                    "This PDF is password protected. Please upload an "
                    "unprotected copy."
                )
            for page in pdf:
                text = page.get_text("text")
                if text:
                    text_chunks.append(text)
    except TextExtractionError:
        raise
    except Exception as exc:
        # Log the detail (which includes the server path) but never surface it.
        logger.warning("PDF extraction failed for %s: %s", pdf_path.name, exc)
        raise TextExtractionError(
            "This file could not be read as a PDF. It may be corrupted or "
            "saved in another format."
        ) from exc

    return "\n".join(text_chunks).strip()


def extract_text_from_txt(file_path: str | Path) -> str:
    """Extract plain text from a .txt file."""
    txt_path = Path(file_path)
    try:
        return txt_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        logger.warning("Text extraction failed for %s: %s", txt_path.name, exc)
        raise TextExtractionError("This text file could not be read.") from exc


def extract_text_from_image(file_path: str | Path) -> str:
    """Extract text from an image file using multiple OCR methods."""
    img_path = Path(file_path)

    ext = img_path.suffix.lower()
    fmt_map = {
        ".png": "png",
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".gif": "gif",
        ".bmp": "bmp",
        ".tiff": "tiff",
        ".tif": "tiff",
    }
    fmt = fmt_map.get(ext, "png")

    with open(img_path, "rb") as f:
        img_data = f.read()

    try:
        doc = fitz.open(stream=img_data, filetype=fmt)
        text_chunks: list[str] = []
        for page in doc:
            text = page.get_text("text")
            if text:
                text_chunks.append(text)
        doc.close()
        result = "\n".join(text_chunks).strip()
        if result:
            return result
    except Exception:
        pass

    try:
        from ai_job_intelligence.services.ai_service import ocr_image
        result = ocr_image(str(img_path))
        if result:
            return result
    except Exception:
        pass

    try:
        import pytesseract  # type: ignore
        from PIL import Image
        import io

        image = Image.open(io.BytesIO(img_data))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception:
        pass

    return ""


def extract_text_from_file(file_path: str | Path) -> str:
    """Extract text from a file based on its extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".txt":
        return extract_text_from_txt(file_path)
    elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif"):
        return extract_text_from_image(file_path)
    else:
        raise TextExtractionError(f"Unsupported file type: {ext}")
