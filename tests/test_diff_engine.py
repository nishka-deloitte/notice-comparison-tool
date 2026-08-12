"""Tests for the diff engine."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.diff_engine import compare_notices


def test_compare_notices_returns_structure() -> None:
    """The diff engine should return a structured comparison result."""
    left = {"data": {"title": "Notice A"}}
    right = {"data": {"title": "Notice B"}}

    result = compare_notices(left, right)

    assert "status" in result
    assert "summary" in result
    assert "differences" in result
    assert "classification" in result


def test_compare_notices_detects_nested_mismatches() -> None:
    """Nested fields should produce field-level mismatch entries."""
    left = {"data": {"title": "Notice A", "amount": 100, "party": {"name": "Acme"}}}
    right = {"data": {"title": "Notice B", "amount": 100, "party": {"name": "Acme"}}}

    result = compare_notices(left, right)

    assert result["status"] == "mismatch"
    assert any(entry["field"] == "data.title" and entry["status"] == "mismatch" for entry in result["differences"])
    assert any(entry["field"] == "data.amount" and entry["status"] == "match" for entry in result["differences"])


def test_compare_notices_handles_missing_keys_and_type_mismatches() -> None:
    """Missing keys and type mismatches should be captured explicitly."""
    left = {"data": {"title": "Notice A", "effective_date": "2026-01-01"}}
    right = {"data": {"title": "Notice A", "effective_date": 20260101}}

    result = compare_notices(left, right)

    matching = [entry for entry in result["differences"] if entry["field"] == "data.effective_date"]
    assert len(matching) == 1
    assert matching[0]["status"] == "mismatch"
    assert matching[0]["value_a"] == "2026-01-01"
    assert matching[0]["value_b"] == 20260101


def test_compare_notices_marks_missing_fields() -> None:
    """Fields missing on either side should be reported as missing."""
    left = {"data": {"title": "Notice A"}}
    right = {"data": {"title": "Notice A", "deadline": "2026-02-01"}}

    result = compare_notices(left, right)

    missing_entry = next(entry for entry in result["differences"] if entry["field"] == "data.deadline")
    assert missing_entry["status"] == "missing"
    assert missing_entry["missing_in"] == "left"
    assert missing_entry["value_a"] is None
    assert missing_entry["value_b"] == "2026-02-01"


def test_compare_notices_uses_union_of_keys_for_same_key_mismatch() -> None:
    """Fields present in both notices should be compared regardless of schema assumptions."""
    left = {"notice_id": "N-100", "recipient": "Acme Corp"}
    right = {"notice_id": "N-200", "recipient": "Acme Corp"}

    result = compare_notices(left, right)

    mismatch = next(entry for entry in result["differences"] if entry["field"] == "notice_id")
    assert mismatch["status"] == "mismatch"
    assert mismatch["value_a"] == "N-100"
    assert mismatch["value_b"] == "N-200"


def test_compare_notices_flags_missing_keys_in_only_one_notice() -> None:
    """A field present in only one notice should be marked as missing in the other."""
    left = {"notice_id": "N-100", "recipient": "Acme Corp"}
    right = {"recipient": "Acme Corp", "amount_due": "$400"}

    result = compare_notices(left, right)

    missing_notice_id = next(entry for entry in result["differences"] if entry["field"] == "notice_id")
    assert missing_notice_id["status"] == "missing"
    assert missing_notice_id["missing_in"] == "right"
    assert missing_notice_id["value_a"] == "N-100"
    assert missing_notice_id["value_b"] is None

    missing_amount_due = next(entry for entry in result["differences"] if entry["field"] == "amount_due")
    assert missing_amount_due["status"] == "missing"
    assert missing_amount_due["missing_in"] == "left"
    assert missing_amount_due["value_a"] is None
    assert missing_amount_due["value_b"] == "$400"


def test_compare_notices_handles_disjoint_key_sets() -> None:
    """Totally different key sets should still be compared across the union."""
    left = {"notice_id": "N-100"}
    right = {"recipient": "Acme Corp"}

    result = compare_notices(left, right)

    notice_id_missing = next(entry for entry in result["differences"] if entry["field"] == "notice_id")
    recipient_missing = next(entry for entry in result["differences"] if entry["field"] == "recipient")

    assert notice_id_missing["status"] == "missing"
    assert notice_id_missing["missing_in"] == "right"
    assert recipient_missing["status"] == "missing"
    assert recipient_missing["missing_in"] == "left"


def test_compare_notices_handles_completely_different_field_sets() -> None:
    """Unrelated schemas should compare across the union without crashing or dropping labels."""
    left = {"notice id": "N-100", "recipient": "Jane Doe"}
    right = {"amount due": "$1,250.00", "due date": "2026-01-15"}

    result = compare_notices(left, right)

    fields = {entry["field"] for entry in result["differences"]}
    assert {"notice id", "recipient", "amount due", "due date"}.issubset(fields)
    assert all(entry["status"] == "missing" for entry in result["differences"])


def test_metadata_is_excluded_from_comparison() -> None:
    """Ensure `metadata` keys are not included in diff comparisons."""
    left = {
        "notice_id": "N-900",
        "recipient": "Foo Corp",
        "amount_due": 100,
        "due_date": "2026-07-01",
        "metadata": {"raw_text": "left text", "source": "fitz+easyocr"},
    }

    right = {
        "notice_id": "N-900",
        "recipient": "Foo Corp",
        "amount_due": 100,
        "due_date": "2026-07-01",
        "metadata": {"raw_text": "right text with OCR noise", "source": "fitz+easyocr"},
    }

    result = compare_notices(left, right)

    # Differences should be empty since only metadata differs
    assert result["status"] == "match"
    assert all(not entry["field"].startswith("metadata") for entry in result["differences"])
