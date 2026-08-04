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
