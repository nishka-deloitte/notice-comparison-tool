"""PyMuPDF and EasyOCR-based extraction helpers for notice documents."""

from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Any

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



class ExtractionError(Exception):
    """Raised when notice extraction fails."""


_reader = None


def _strip_raw_text_noise(raw_text: str) -> str:
    """Remove browser/screenshot metadata lines that are not lease content."""
    if not raw_text:
        return ""

    cleaned_lines: list[str] = []
    for line in raw_text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        lower = candidate.lower()
        if "bing.com" in lower or "comlthlid" in lower:
            continue
        if re.search(r"\d{1,2}/\d{1,2}/\d{2,4}\s*,?\s*\d{1,2}:\d{2}\s*(?:am|pm)", lower, flags=re.IGNORECASE):
            continue
        if re.search(r"\b\d{2,5}\s*[xX]\s*\d{2,5}\b", lower):
            continue
        if re.search(r"\b\d+\s*px\b", lower):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


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
    """Run OCR over image bytes and return the combined extracted text.

    Preserve detected text lines as separate lines so the generic label/value parser
    can still process line-by-line OCR output instead of receiving one giant blob.
    """
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
            extracted_parts.append(str(text).strip())

    return "\n".join(part for part in extracted_parts if part)


def _extract_pdf_form_fields(file_bytes: bytes) -> dict[str, str]:
    """Read direct form widget values from a PDF as the highest-confidence field data source."""
    if fitz is None:
        raise ExtractionError("PyMuPDF is not available.")

    document = fitz.open(stream=file_bytes, filetype="pdf")
    form_fields: dict[str, str] = {}
    try:
        for page_index, page in enumerate(document, start=1):
            widgets = list(page.widgets()) if hasattr(page, "widgets") else []
            if not widgets:
                print(f"[widget-debug] page {page_index}: no widgets found")
                logging.info("PDF widget debug: page %s -> no widgets found", page_index)
                continue

            print(f"[widget-debug] page {page_index}: found {len(widgets)} widget(s)")
            for widget_index, widget in enumerate(widgets, start=1):
                field_name = getattr(widget, "field_name", None)
                field_value = getattr(widget, "field_value", None)
                print(
                    f"[widget-debug] page {page_index} widget {widget_index}: "
                    f"field_name={field_name!r}, field_value={field_value!r}"
                )
                logging.info(
                    "PDF widget debug: page %s widget %s -> field_name=%r field_value=%r",
                    page_index,
                    widget_index,
                    field_name,
                    field_value,
                )

                if not field_name or not str(field_name).strip():
                    logging.warning(
                        "Skipping PDF form widget on page %s with missing or blank field_name: %r",
                        page_index,
                        widget,
                    )
                    continue

                label = str(field_name).strip()
                value = str(field_value).strip() if field_value is not None else ""
                form_fields[label] = value
    finally:
        document.close()

    return form_fields


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF by combining native page text and OCR for every page."""
    if fitz is None:
        raise ExtractionError("PyMuPDF is not available.")

    form_fields = _extract_pdf_form_fields(file_bytes)
    document = fitz.open(stream=file_bytes, filetype="pdf")
    page_texts: list[str] = []
    try:
        for page in document:
            page_text = page.get_text().strip()
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            ocr_text = _ocr_image_bytes(pixmap.tobytes("png")).strip()

            parts: list[str] = []
            if page_text:
                parts.append(f"[FITZ_TEXT]\n{page_text}")
            if ocr_text:
                parts.append(f"[OCR_TEXT]\n{ocr_text}")
            if parts:
                page_texts.append("\n\n".join(parts))
    finally:
        document.close()

    combined_parts: list[str] = []
    if form_fields:
        combined_parts.extend(f"{label}: {value}" for label, value in form_fields.items() if value)
    combined_parts.extend(page_texts)

    deduped: list[str] = []
    seen: set[str] = set()
    for part in combined_parts:
        normalized = " ".join(part.split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(part.strip())

    return "\n".join(deduped)


def _extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from a JPEG image with OCR."""
    return _ocr_image_bytes(file_bytes)


def extract_notice_fields(file_bytes: bytes, file_type: str) -> dict[str, Any]:
    """Extract arbitrary label/value pairs from a PDF or JPEG notice."""
    if not file_bytes:
        raise ExtractionError("No file data provided.")

    form_fields: dict[str, str] = {}
    if file_type == "application/pdf":
        form_fields = _extract_pdf_form_fields(file_bytes)
        raw_text = _extract_text_from_pdf(file_bytes)
    elif file_type in {"image/jpeg", "image/jpg"}:
        raw_text = _extract_text_from_image(file_bytes)
    else:
        raise ExtractionError(f"Unsupported file type: {file_type}")

    raw_text = _strip_raw_text_noise(raw_text)

    parsed_fields: dict[str, str] = {}
    for label, value in form_fields.items():
        if not value:
            continue
        parsed_fields[label] = value

    payload: dict[str, Any] = {
        "metadata": {
            "source": "fitz+easyocr",
            "raw_text": raw_text,
            "form_fields": form_fields,
            "unparsed_fields": [],
        }
    }
    for label, value in parsed_fields.items():
        payload[label] = value
    return payload
