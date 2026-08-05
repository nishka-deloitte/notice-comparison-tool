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
    # Strip common trailing punctuation introduced by OCR or surrounding text
    cleaned = cleaned.rstrip(".,;:")
    if not cleaned:
        return None

    try:
        numeric = float(cleaned)
    except ValueError:
        return None

    return int(numeric) if numeric.is_integer() else numeric


def parse_notice_fields(text: str) -> tuple[dict[str, Any], list[str], str | None]:
    """Parse notice fields from raw OCR or PDF text.

    Returns a tuple of (parsed_fields, unparsed_fields).
    """
    json_error: str | None = None
    if not text:
        return {}, ["notice_id", "recipient", "amount_due", "due_date"], None

    # Normalize common OCR substitutions before attempting regex extraction:
    # - replace curly/typographic quotes with straight quotes
    # - replace non-breaking spaces with regular spaces
    # - strip leading/trailing whitespace on each line
    normalized_text = (
        text
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u00A0", " ")
    )
    normalized_text = "\n".join(line.strip() for line in normalized_text.splitlines())

    # Use regex-based, OCR-tolerant extraction for each field.
    # Drop blank lines for regex matching.
    normalized = "\n".join(part for part in normalized_text.splitlines() if part)

    parsed: dict[str, Any] = {}
    unparsed: list[str] = []

    # Patterns follow: allow underscore or space in field name,
    # allow separators :, =, - with optional whitespace, optional wrapping quotes,
    # capture up to next comma, quote, or linebreak.
    # Allow explicit separators (:, =, -) or just whitespace as a separator
    sep = r"(?:[:=\-]|\s)"
    notice_id_patterns = [
        rf"notice[_ ]id\s*[\"']?\s*{sep}\s*[\"']?([^,\"'\n]+)",
    ]
    # Allow commas inside recipient names (e.g., "Last, Jr.") so exclude only
    # quotes and newlines from the capture for recipient. For amounts, capture
    # only numeric/currency characters to keep internal commas/periods.
    recipient_patterns = [
        rf"recipient\s*[\"']?\s*{sep}\s*[\"']?([^\"'\n]+)",
        rf"to\s*[\"']?\s*{sep}\s*[\"']?([^\"'\n]+)",
    ]
    amount_patterns = [
        rf"amount[_ ]due\s*[\"']?\s*{sep}\s*[\"']?([\$0-9,\.]+)",
        rf"amount\s*[\"']?\s*{sep}\s*[\"']?([\$0-9,\.]+)",
        rf"balance\s*[\"']?\s*{sep}\s*[\"']?([\$0-9,\.]+)",
    ]
    # Only match explicit "due date" or "date due" fields — avoid matching
    # other fields like "issue_date" which also contain the word "date".
    due_date_patterns = [
        rf"due[_ ]date\s*[\"']?\s*{sep}\s*[\"']?([^,\"'\n]+)",
        rf"date[_ ]due\s*[\"']?\s*{sep}\s*[\"']?([^,\"'\n]+)",
    ]

    notice_id = _first_match(normalized, notice_id_patterns)
    if notice_id:
        parsed["notice_id"] = notice_id.strip()
    else:
        unparsed.append("notice_id")

    recipient = _first_match(normalized, recipient_patterns)
    if recipient:
        # Trim any trailing content that looks like the next field (amount/due)
        tail_split = re.split(r"\b(?:amount|balance|due|issue|notice)\b", recipient, flags=re.IGNORECASE)
        parsed["recipient"] = tail_split[0].strip()
    else:
        unparsed.append("recipient")

    amount_val = _first_match(normalized, amount_patterns)
    parsed_amount = _parse_amount(amount_val.strip() if amount_val else None)
    if parsed_amount is not None:
        parsed["amount_due"] = parsed_amount
    else:
        unparsed.append("amount_due")

    due_date = _first_match(normalized, due_date_patterns)
    if due_date:
        parsed["due_date"] = due_date.strip()
    else:
        unparsed.append("due_date")

    return parsed, unparsed, json_error
