"""Lightweight parsing rules for extracting notice fields from raw text."""

from __future__ import annotations

import json
import re
from typing import Any


def _first_match(text: str, patterns: list[str]) -> str | None:
    """Return the first matching group from a list of regex patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _parse_amount(value: str | None) -> float | int | None:
    """Parse monetary values into a number."""
    if not value:
        return None

    cleaned = value.replace(",", "").replace("$", "").strip()
    if not cleaned:
        return None

    try:
        numeric = float(cleaned)
    except ValueError:
        return None

    return int(numeric) if numeric.is_integer() else numeric


def parse_notice_fields(text: str) -> tuple[dict[str, Any], list[str]]:
    """Parse notice fields from raw OCR or PDF text.

    Returns a tuple of (parsed_fields, unparsed_fields).
    """
    if not text:
        return {}, ["notice_id", "recipient", "amount_due", "due_date"]

    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed_json = json.loads(stripped)
            if isinstance(parsed_json, dict):
                parsed_fields: dict[str, Any] = {}
                unparsed_fields: list[str] = []

                if "notice_id" in parsed_json:
                    parsed_fields["notice_id"] = parsed_json["notice_id"]
                else:
                    unparsed_fields.append("notice_id")

                if "recipient" in parsed_json:
                    parsed_fields["recipient"] = parsed_json["recipient"]
                else:
                    unparsed_fields.append("recipient")

                if "amount_due" in parsed_json:
                    parsed_fields["amount_due"] = _parse_amount(str(parsed_json["amount_due"])) if parsed_json["amount_due"] is not None else None
                    if parsed_fields["amount_due"] is None:
                        unparsed_fields.append("amount_due")
                else:
                    unparsed_fields.append("amount_due")

                if "due_date" in parsed_json:
                    parsed_fields["due_date"] = parsed_json["due_date"]
                else:
                    unparsed_fields.append("due_date")

                return parsed_fields, unparsed_fields
        except json.JSONDecodeError:
            pass

    normalized = "\n".join(part.strip() for part in text.splitlines() if part.strip())
    parsed: dict[str, Any] = {}
    unparsed: list[str] = []

    notice_id = _first_match(
        normalized,
        [
            r"notice(?:\s+id)?\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
            r"id\s*number\s*[:#-]?\s*([A-Za-z0-9\-/]+)",
        ],
    )
    if notice_id:
        parsed["notice_id"] = notice_id
    else:
        unparsed.append("notice_id")

    recipient = _first_match(
        normalized,
        [
            r"recipient\s*[:#-]?\s*([A-Za-z0-9 .,&-]+)",
            r"to\s+([A-Za-z0-9 .,&-]+)",
        ],
    )
    if recipient:
        parsed["recipient"] = recipient
    else:
        unparsed.append("recipient")

    amount_due = _first_match(
        normalized,
        [
            r"amount\s+due\s*[:#-]?\s*\$?([0-9,]+(?:\.\d{1,2})?)",
            r"amount\s*[:#-]?\s*\$?([0-9,]+(?:\.\d{1,2})?)",
            r"balance\s*[:#-]?\s*\$?([0-9,]+(?:\.\d{1,2})?)",
        ],
    )
    parsed_amount = _parse_amount(amount_due)
    if parsed_amount is not None:
        parsed["amount_due"] = parsed_amount
    else:
        unparsed.append("amount_due")

    due_date = _first_match(
        normalized,
        [
            r"due\s+date\s*[:#-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
            r"date\s+due\s*[:#-]?\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})",
        ],
    )
    if due_date:
        parsed["due_date"] = due_date
    else:
        unparsed.append("due_date")

    return parsed, unparsed
