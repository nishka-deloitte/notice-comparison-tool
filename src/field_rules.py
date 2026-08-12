"""Generic parsing rules for extracting arbitrary label/value pairs from raw text."""

from __future__ import annotations

import re


def _normalize_label(label: str) -> str:
    """Normalize a field label so similar labels compare equal across OCR noise."""
    normalized = label.strip().lower().replace("_", " ")
    normalized = re.sub(r"[-/]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _clean_value(value: str) -> str:
    """Remove common wrapping quotes/punctuation while keeping meaningful text intact."""
    cleaned = value.strip()
    while len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {'"', "'", "`"}:
        cleaned = cleaned[1:-1].strip()
    cleaned = re.sub(r"^[:=\-\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.rstrip(".,;:")
    return cleaned.strip()


def _is_header_like(label: str, value: str) -> bool:
    """Reject common non-field headings like page headers or document titles."""
    header_labels = {
        "page",
        "page of",
        "notice",
        "notice of",
        "document",
        "section",
        "heading",
        "title",
    }
    if label in header_labels:
        return True
    if re.fullmatch(r"page\s+\d+\s+of\s+\d+", label, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"notice\s+of\b.*", label, flags=re.IGNORECASE):
        return True
    if label.startswith("page ") and re.fullmatch(r"\d+", value):
        return True
    return False


def _is_label_candidate(label: str) -> bool:
    """Reject narrative or sentence-like fragments that are not field labels."""
    if not label or len(label) < 2:
        return False

    tokens = [token for token in re.split(r"[\s_./&()\-]+", label) if token]
    if not tokens:
        return False

    sentence_like_keywords = {
        "this", "that", "there", "here", "with", "without", "from", "into",
        "just", "only", "does", "did", "has", "have", "are", "is", "was",
        "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "at",
        "no", "not", "but", "if", "when", "then",
    }
    if any(token.lower() in sentence_like_keywords for token in tokens):
        return False
    if len(tokens) > 5:
        return False
    return True


def _is_noise_line(candidate: str) -> bool:
    """Reject technical markers and metadata noise that leak into OCR or page text."""
    if not candidate:
        return True

    normalized = candidate.strip()
    if not normalized:
        return True

    lower = normalized.lower()
    if lower.startswith("[fitz_text]") or lower.startswith("[ocr_text]"):
        return True
    if lower.startswith("http://") or lower.startswith("https://") or lower.startswith("www."):
        return True

    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?(?:\s?[ap]m)?", normalized, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[ap]m)?", normalized, flags=re.IGNORECASE):
        return True
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s?[ap]m)?", normalized, flags=re.IGNORECASE):
        return True

    return False


def _match_line(line: str) -> tuple[str, str] | None:
    """Return a (normalized_label, value) tuple when the line matches a generic label/value pattern."""
    candidate = line.strip()
    if not candidate or len(candidate) < 3:
        return None
    if _is_noise_line(candidate):
        return None

    if re.fullmatch(r"[-*_#=]+", candidate):
        return None

    loose_match = re.split(r"\s{2,}", candidate, maxsplit=1)
    if len(loose_match) == 2:
        label, value = loose_match
        label = label.strip()
        value = _clean_value(value)
        if not label or not value:
            return None

        normalized_label = _normalize_label(label)
        if not _is_label_candidate(normalized_label):
            return None
        if _is_header_like(normalized_label, value):
            return None
        return normalized_label, value

    patterns = [
        r"^(?P<label>[A-Za-z0-9][A-Za-z0-9\s_./&()\-]*?[A-Za-z0-9])\s*(?P<sep>[:=]|[-]{1,3}|[/]{1,3}|[;]{1,3})\s*(?P<value>.+?)\s*$",
    ]

    for pattern_text in patterns:
        match = re.match(pattern_text, candidate, flags=re.IGNORECASE)
        if not match:
            continue

        label = match.group("label").strip()
        if not label:
            continue

        normalized_label = _normalize_label(label)
        value = _clean_value(match.group("value"))
        if not normalized_label or not value:
            continue
        if not _is_label_candidate(normalized_label):
            continue
        if _is_header_like(normalized_label, value):
            continue
        if len(normalized_label.split()) > 6:
            continue
        return normalized_label, value

    return None


def parse_notice_fields(raw_text: str) -> dict[str, str]:
    """Parse arbitrary label/value entries from OCR or PDF text.

    The parser scans each line for a generic pattern of label + separator + value,
    normalizes the label for comparison, and ignores non-matching lines.
    """
    if not raw_text:
        return {}

    parsed: dict[str, str] = {}
    for line in raw_text.splitlines():
        match = _match_line(line)
        if match is None:
            continue

        label, value = match
        parsed[label] = value

    return parsed
