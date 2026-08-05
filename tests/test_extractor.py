"""Tests for the PyMuPDF/EasyOCR notice extractor."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import extractor


def test_extract_notice_fields_parses_pdf_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF input should be converted to text and parsed into a notice dict."""
    monkeypatch.setattr(
        extractor,
        "_extract_text_from_pdf",
        lambda file_bytes: "Notice ID: N-001\nRecipient: Acme Corp\nAmount Due: $1500\nDue Date: 2026-08-15",
    )

    result = extractor.extract_notice_fields(b"%PDF-1.4 fake", "application/pdf")

    assert result["notice_id"] == "N-001"
    assert result["recipient"] == "Acme Corp"
    assert result["amount_due"] == 1500
    assert result["due_date"] == "2026-08-15"
    assert result["metadata"]["unparsed_fields"] == []


def test_extract_notice_fields_parses_jpeg_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """JPEG input should be OCRed and parsed into a notice dict."""
    monkeypatch.setattr(
        extractor,
        "_extract_text_from_image",
        lambda file_bytes: "Recipient: Globex\nAmount Due: 2000\nDue Date: 2026-09-01",
    )

    result = extractor.extract_notice_fields(b"fake-jpeg", "image/jpeg")

    assert result["notice_id"] is None
    assert result["recipient"] == "Globex"
    assert result["amount_due"] == 2000
    assert result["due_date"] == "2026-09-01"
    assert "notice_id" in result["metadata"]["unparsed_fields"]


def test_extract_notice_fields_parses_json_text_directly(monkeypatch: pytest.MonkeyPatch) -> None:
    """Raw JSON text should be parsed directly into notice fields."""
    monkeypatch.setattr(
        extractor,
        "_extract_text_from_pdf",
        lambda file_bytes: '{"notice_id": "N-1001", "recipient": "Umbrella Corp", "amount_due": 150.00, "due_date": "2026-10-01"}',
    )

    result = extractor.extract_notice_fields(b"%PDF-1.4 fake", "application/pdf")

    assert result["notice_id"] == "N-1001"
    assert result["recipient"] == "Umbrella Corp"
    assert result["amount_due"] == 150
    assert result["due_date"] == "2026-10-01"
    assert result["metadata"]["unparsed_fields"] == []


def test_extract_notice_fields_raises_for_unsupported_type() -> None:
    """Unsupported file types should raise a clear extraction error."""
    with pytest.raises(extractor.ExtractionError, match="Unsupported file type"):
        extractor.extract_notice_fields(b"fake", "text/plain")


def test_cross_format_consistency(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF and JPEG OCR of the same notice should produce the same parsed fields."""
    pdf_text = "Notice ID: N-500\nRecipient: ACME Corp\nAmount Due: $50\nDue Date: 2026-12-01"
    jpeg_text = 'notice id = "N-500" recipient: ACME Corp amount due $50 due date 2026-12-01'

    monkeypatch.setattr(extractor, "_extract_text_from_pdf", lambda file_bytes: pdf_text)
    monkeypatch.setattr(extractor, "_extract_text_from_image", lambda file_bytes: jpeg_text)

    pdf_result = extractor.extract_notice_fields(b"%PDF-1.4 fake", "application/pdf")
    img_result = extractor.extract_notice_fields(b"fake-jpeg", "image/jpeg")

    assert pdf_result["notice_id"] == img_result["notice_id"] == "N-500"
    assert pdf_result["recipient"] == img_result["recipient"] == "ACME Corp"
    assert pdf_result["amount_due"] == img_result["amount_due"] == 50
    assert pdf_result["due_date"] == img_result["due_date"] == "2026-12-01"
