"""PyMuPDF and EasyOCR-based extraction helpers for notice documents."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from dotenv import load_dotenv

load_dotenv()

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - exercised if dependency is missing
    fitz = None  # type: ignore[assignment]

try:
    import easyocr  # type: ignore
except ImportError:  # pragma: no cover - exercised if dependency is missing
    easyocr = None  # type: ignore[assignment]

try:
    from PIL import Image  # type: ignore
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover - exercised if dependency is missing
    Image = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]

from src.field_rules import parse_notice_fields


class ExtractionError(Exception):
    """Raised when notice extraction fails."""


REQUIRED_FIELDS = ("notice_id", "recipient", "amount_due", "due_date")

_reader = None


def _get_reader() -> Any:
    """Return a cached EasyOCR reader instance."""
    global _reader
    if _reader is None:
        if easyocr is None:
            raise ExtractionError("easyocr is not available.")
        try:
            _reader = easyocr.Reader(["en"])
        except Exception as exc:  # pragma: no cover - exercised by environment issues
            raise ExtractionError(f"Unable to initialize EasyOCR: {exc}") from exc
    return _reader


def _ocr_image_bytes(image_bytes: bytes) -> str:
    """Run OCR over image bytes and return the combined extracted text."""
    if Image is None or np is None:
        raise ExtractionError("Pillow and NumPy are required for OCR.")

    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(image)
    results = _get_reader().readtext(image_array)

    extracted_parts: list[str] = []
    for entry in results:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            text = entry[1]
        else:
            text = str(entry)
        if text:
            extracted_parts.append(str(text))

    return " ".join(extracted_parts)


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF, falling back to OCR for scanned pages."""
    if fitz is None:
        raise ExtractionError("PyMuPDF is not available.")

    document = fitz.open(stream=file_bytes, filetype="pdf")
    page_texts: list[str] = []
    try:
        for page in document:
            page_text = page.get_text()
            if len(page_text.strip()) < 40:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                page_texts.append(_ocr_image_bytes(pixmap.tobytes("png")))
            else:
                page_texts.append(page_text)
    finally:
        document.close()

    return "\n".join(page_texts)


def _extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from a JPEG image with OCR."""
    return _ocr_image_bytes(file_bytes)


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize extracted fields into the notice schema."""
    normalized = {
        "notice_id": payload.get("notice_id"),
        "recipient": payload.get("recipient"),
        "amount_due": payload.get("amount_due"),
        "due_date": payload.get("due_date"),
    }

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if not isinstance(metadata.get("unparsed_fields"), list):
        metadata["unparsed_fields"] = []
    normalized["metadata"] = metadata
    return normalized


def extract_notice_fields(file_bytes: bytes, file_type: str) -> dict[str, Any]:
    """Extract notice fields from a PDF or JPEG document using PyMuPDF and EasyOCR."""
    if not file_bytes:
        raise ExtractionError("No file data provided.")

    if file_type == "application/pdf":
        raw_text = _extract_text_from_pdf(file_bytes)
    elif file_type in {"image/jpeg", "image/jpg"}:
        raw_text = _extract_text_from_image(file_bytes)
    else:
        raise ExtractionError(f"Unsupported file type: {file_type}")

    parsed_fields, unparsed_fields = parse_notice_fields(raw_text)
    payload = {
        "notice_id": parsed_fields.get("notice_id"),
        "recipient": parsed_fields.get("recipient"),
        "amount_due": parsed_fields.get("amount_due"),
        "due_date": parsed_fields.get("due_date"),
        "metadata": {
            "source": "fitz+easyocr",
            "raw_text": raw_text,
            "unparsed_fields": unparsed_fields,
        },
    }

    return _normalize_payload(payload)
