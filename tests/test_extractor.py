"""Tests for the PyMuPDF/RapidOCR notice extractor."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import extractor


def test_extract_notice_fields_parses_pdf_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF structured output should come only from actual form widgets, never from prose/OCR line parsing."""
    monkeypatch.setattr(
        extractor,
        "_extract_pdf_form_fields",
        lambda file_bytes: {"notice_id": "N-001", "recipient": "Acme Corp", "amount_due": "$1500"},
    )
    monkeypatch.setattr(
        extractor,
        "_extract_text_from_pdf",
        lambda file_bytes: "Notice ID: N-001\nRecipient: Acme Corp\nPURPOSE: Rent is due monthly\n8/11/26, 11:06 AM\nhttps://bing.com",
    )

    result = extractor.extract_notice_fields(b"%PDF-1.4 fake", "application/pdf")

    assert result["notice_id"] == "N-001"
    assert result["recipient"] == "Acme Corp"
    assert result["amount_due"] == "$1500"
    assert "PURPOSE" not in result
    assert "Notice ID" not in result
    assert "bing.com" not in result["metadata"]["raw_text"].lower()
    assert result["metadata"]["unparsed_fields"] == []


def test_extract_notice_fields_parses_jpeg_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """JPEG input keeps prose/OCR text only in metadata.raw_text; it does not create structured fields without form widgets."""
    monkeypatch.setattr(
        extractor,
        "_extract_text_from_image",
        lambda file_bytes: "Recipient: Globex\nAmount Due: 2000\nDue Date: 2026-09-01",
    )

    result = extractor.extract_notice_fields(b"fake-jpeg", "image/jpeg")

    assert result["metadata"]["raw_text"] == "Recipient: Globex\nAmount Due: 2000\nDue Date: 2026-09-01"
    assert "recipient" not in result
    assert "amount due" not in result
    assert "due date" not in result
    assert "notice id" not in result


def test_extract_notice_fields_raises_for_unsupported_type() -> None:
    """Unsupported file types should raise a clear extraction error."""
    with pytest.raises(extractor.ExtractionError, match="Unsupported file type"):
        extractor.extract_notice_fields(b"fake", "text/plain")


def test_ocr_image_bytes_uses_rapidocr_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """OCR should call the module-level RapidOCR instance and extract the text payload from each result entry."""

    class FakeImageData:
        def convert(self, mode):
            return self

    class FakeImage:
        @staticmethod
        def open(_):
            return FakeImageData()

    class FakeNumpy:
        @staticmethod
        def array(value):
            return [1, 2, 3]

    def fake_engine(image_array):
        assert image_array == [1, 2, 3]
        return ([([1, 2], "First line", 0.99), ([3, 4], "Second line", 0.88)], None)

    monkeypatch.setattr(extractor, "Image", FakeImage)
    monkeypatch.setattr(extractor, "np", FakeNumpy)
    monkeypatch.setattr(extractor, "_ocr_engine", fake_engine)

    assert extractor._ocr_image_bytes(b"fake-image") == "First line\nSecond line"


def test_extract_notice_fields_collects_pdf_form_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF widgets should be captured as high-confidence form field values and merged into parsed output."""

    class FakeWidget:
        def __init__(self, field_name: str, field_value: str) -> None:
            self.field_name = field_name
            self.field_value = field_value

    class FakePage:
        def widgets(self):
            return [
                FakeWidget("tenant_name", "Acme Corp"),
                FakeWidget("lease_amount", "$1,250.00"),
            ]

        def get_text(self):
            return "This is a lease template.\nTenant Name: Acme Corp\n"

        def get_pixmap(self, matrix, alpha):
            class FakePixmap:
                def tobytes(self, fmt: str) -> bytes:
                    return b"fake-image"

            return FakePixmap()

    class FakeDocument:
        def __init__(self) -> None:
            self.pages = [FakePage()]

        def __iter__(self):
            return iter(self.pages)

        def close(self):
            pass

    monkeypatch.setattr(extractor, "fitz", type("FitzStub", (), {"open": staticmethod(lambda stream, filetype: FakeDocument()), "Matrix": lambda *args, **kwargs: object()}))
    monkeypatch.setattr(extractor, "_ocr_image_bytes", lambda image_bytes: "Lease template text\nTenant Name: Acme Corp")

    result = extractor.extract_notice_fields(b"fake-pdf", "application/pdf")

    assert result["metadata"]["form_fields"]["tenant_name"] == "Acme Corp"
    assert result["metadata"]["form_fields"]["lease_amount"] == "$1,250.00"
    assert result["tenant_name"] == "Acme Corp"
    assert result["lease_amount"] == "$1,250.00"


def test_extract_notice_fields_merges_page_text_and_ocr_for_mixed_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """A page with some embedded text and scanned content should include both fitz and OCR output instead of picking one exclusively."""

    class FakePage:
        def get_text(self):
            return "Lease Agreement\n"

        def get_pixmap(self, matrix, alpha):
            class FakePixmap:
                def tobytes(self, fmt: str) -> bytes:
                    return b"fake-image"

            return FakePixmap()

    class FakeDocument:
        def __init__(self) -> None:
            self.pages = [FakePage()]

        def __iter__(self):
            return iter(self.pages)

        def close(self):
            pass

    monkeypatch.setattr(extractor, "fitz", type("FitzStub", (), {"open": staticmethod(lambda stream, filetype: FakeDocument()), "Matrix": lambda *args, **kwargs: object()}))
    monkeypatch.setattr(extractor, "_ocr_image_bytes", lambda image_bytes: "Tenant pays rent on the first day of each month")

    result = extractor.extract_notice_fields(b"fake-pdf", "application/pdf")

    assert "[FITZ_TEXT]" in result["metadata"]["raw_text"]
    assert "Lease Agreement" in result["metadata"]["raw_text"]
    assert "[OCR_TEXT]" in result["metadata"]["raw_text"]
    assert "Tenant pays rent on the first day of each month" in result["metadata"]["raw_text"]


def test_cross_format_consistency(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF form-fields and JPEG raw text occupy different channels; only real form values become structured fields."""
    pdf_fields = {"notice_id": "N-500", "recipient": "ACME Corp", "amount_due": "$50"}
    jpeg_text = "notice id = N-500\nrecipient: ACME Corp\namount due = $50\ndue date = 2026-12-01"

    monkeypatch.setattr(extractor, "_extract_pdf_form_fields", lambda file_bytes: pdf_fields)
    monkeypatch.setattr(extractor, "_extract_text_from_pdf", lambda file_bytes: "Notice ID: N-500\nRecipient: ACME Corp\nAmount Due: $50")
    monkeypatch.setattr(extractor, "_extract_text_from_image", lambda file_bytes: jpeg_text)

    pdf_result = extractor.extract_notice_fields(b"%PDF-1.4 fake", "application/pdf")
    img_result = extractor.extract_notice_fields(b"fake-jpeg", "image/jpeg")

    assert pdf_result["notice_id"] == "N-500"
    assert pdf_result["recipient"] == "ACME Corp"
    assert pdf_result["amount_due"] == "$50"
    assert "notice id" not in img_result
    assert "recipient" not in img_result
    assert "due date" not in img_result
