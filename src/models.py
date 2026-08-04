"""Data models and typing helpers for the Notice Comparison Tool."""

from __future__ import annotations

from typing import Any, TypedDict


class NoticePayload(TypedDict, total=False):
    """Shape for a notice extraction result."""

    notice_id: str
    version: str
    metadata: dict[str, Any]
    data: dict[str, Any]


class DifferenceEntry(TypedDict, total=False):
    """Represents one field-level difference."""

    path: str
    change_type: str
    before: Any
    after: Any


class ComparisonResult(TypedDict, total=False):
    """Structured comparison result returned by the diff engine."""

    status: str
    summary: str
    differences: list[DifferenceEntry]
    classification: dict[str, Any]
