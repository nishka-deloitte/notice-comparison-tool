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
    assert missing_entry["value_a"] is None
    assert missing_entry["value_b"] == "2026-02-01"
