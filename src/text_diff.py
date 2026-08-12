"""Paragraph-level diffing helpers for comparing full document text."""

from __future__ import annotations

import difflib
from typing import Any


def _merge_short_lines(lines: list[str]) -> list[str]:
    """Merge consecutive short address/label lines into a single logical block."""
    if not lines:
        return []

    merged: list[str] = []
    buffer = ""

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer.strip():
            merged.append(buffer.strip())
        buffer = ""

    for line in lines:
        candidate = line.strip()
        if not candidate:
            continue

        words = candidate.split()
        ends_with_sentence = candidate.endswith((".", "!", "?"))
        is_short = len(words) <= 9 and not ends_with_sentence

        if is_short and buffer:
            buffer = f"{buffer} {candidate}"
            continue

        if is_short and not buffer:
            buffer = candidate
            continue

        if buffer:
            flush_buffer()
        merged.append(candidate)

    flush_buffer()
    return merged


def _split_paragraphs(text: str) -> list[str]:
    """Split raw text into paragraph-like units.

    Prefer double-newline boundaries, then merge loosely-related short lines so
    clusters like an address or a list of tenant details are diffed as a single
    coherent block instead of dozens of fragmented one-line entries.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return []

    paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    if len(paragraphs) > 1:
        merged: list[str] = []
        for part in paragraphs:
            lines = [line.strip() for line in part.split("\n") if line.strip()]
            merged.extend(_merge_short_lines(lines))
        return merged

    fallback = [part.strip() for part in cleaned.split("\n") if part.strip()]
    return _merge_short_lines(fallback) or [cleaned]


def _word_diff(text_a: str, text_b: str) -> list[str]:
    """Return a word-level ndiff list for a changed paragraph."""
    words_a = text_a.split()
    words_b = text_b.split()
    return list(difflib.ndiff(words_a, words_b))


def _word_overlap(text_a: str, text_b: str) -> set[str]:
    """Return the overlapping word stems between two paragraphs."""
    words_a = {word.lower() for word in (text_a or "").split() if word}
    words_b = {word.lower() for word in (text_b or "").split() if word}
    return words_a & words_b


def _classify_entry(entry: dict[str, Any]) -> str:
    """Classify a diff entry for summary counts, including blank/no-overlap cases."""
    status = entry.get("status")
    if status in {"removed", "added", "unchanged"}:
        return status

    if status != "changed":
        return "changed"

    text_a = entry.get("text_a") or ""
    text_b = entry.get("text_b") or ""
    if not text_a.strip() and not text_b.strip():
        return "unchanged"
    if not text_a.strip():
        return "added"
    if not text_b.strip():
        return "removed"
    if not _word_overlap(text_a, text_b):
        if len((text_a or "").split()) >= len((text_b or "").split()):
            return "removed"
        return "added"
    return "changed"


def group_text_diff_entries(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group diff entries into the main categories shown to users."""
    grouped: dict[str, list[dict[str, Any]]] = {
        "only_in_a": [],
        "only_in_b": [],
        "changed": [],
        "unchanged": [],
    }

    for entry in entries:
        status = _classify_entry(entry)
        if status == "removed":
            grouped["only_in_a"].append(entry)
        elif status == "added":
            grouped["only_in_b"].append(entry)
        elif status == "changed":
            grouped["changed"].append(entry)
        elif status == "unchanged":
            grouped["unchanged"].append(entry)

    return grouped


def build_text_diff_summary(entries: list[dict[str, Any]]) -> str:
    """Return the plain-language summary used at the top of the text comparison view."""
    grouped = group_text_diff_entries(entries)
    only_in_a = len(grouped["only_in_a"])
    only_in_b = len(grouped["only_in_b"])
    changed = len(grouped["changed"])

    return (
        f"Document A has {only_in_a} sections/lines not found in Document B, and Document B has {only_in_b} "
        f"sections/lines not found in Document A. {changed} sections have minor wording differences."
    )


def render_word_diff_for_side(text_a: str, text_b: str, side: str) -> str:
    """Render the word-level diff for one side of a changed paragraph.

    - side="a": show Document A words, with removed words struck through.
    - side="b": show Document B words, with added words highlighted.
    """
    if side not in {"a", "b"}:
        return ""

    text_a = text_a or ""
    text_b = text_b or ""

    if side == "a" and not text_a.strip():
        return "<span style='color:#6c757d;'>(blank in Document A)</span>"
    if side == "b" and not text_b.strip():
        return "<span style='color:#6c757d;'>(blank in Document B)</span>"

    words_a = text_a.split()
    words_b = text_b.split()
    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    rendered: list[str] = []

    def render_token(token: str, style: str) -> str:
        value = token
        if style == "removed":
            return (
                "<span style='text-decoration: line-through; color: #1a1a1a; background: #f8d7da; "
                "padding: 0 2px; border-radius: 2px;'>{}</span>".format(value)
            )
        if style == "added":
            return (
                "<span style='color: #1a1a1a; background: #d4edda; padding: 0 2px; border-radius: 2px;'>{}</span>"
                .format(value)
            )
        return "<span style='color: #1a1a1a;'>{}</span>".format(value)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if side == "a":
            if tag == "equal":
                rendered.extend(render_token(token, "plain") for token in words_a[i1:i2])
            elif tag in {"replace", "delete"}:
                rendered.extend(render_token(token, "removed") for token in words_a[i1:i2])
            elif tag == "insert":
                continue
        else:
            if tag == "equal":
                rendered.extend(render_token(token, "plain") for token in words_b[j1:j2])
            elif tag in {"replace", "insert"}:
                rendered.extend(render_token(token, "added") for token in words_b[j1:j2])
            elif tag == "delete":
                continue

    return " ".join(rendered) if rendered else "<span style='color:#6c757d;'>(blank)</span>"


def compare_full_text(text_a: str, text_b: str) -> list[dict[str, Any]]:
    """Compare full document text at the paragraph level.

    The first input is treated as Document A, so sections present only in A are
    labeled as "removed" and sections present only in B are labeled as "added".
    For changed paragraphs, a word-level diff is included in the returned dict to
    show small wording changes inside a paragraph.
    """
    paragraphs_a = _split_paragraphs(text_a)
    paragraphs_b = _split_paragraphs(text_b)

    if not paragraphs_a and not paragraphs_b:
        return []

    matcher = difflib.SequenceMatcher(None, paragraphs_a, paragraphs_b)
    result: list[dict[str, Any]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for idx in range(i1, i2):
                paragraph_a = paragraphs_a[idx]
                paragraph_b = paragraphs_b[j1 + (idx - i1)]
                result.append(
                    {
                        "status": "unchanged",
                        "text_a": paragraph_a,
                        "text_b": paragraph_b,
                        "word_diff": [],
                    }
                )
        elif tag == "replace":
            max_length = max(i2 - i1, j2 - j1)
            for offset in range(max_length):
                paragraph_a = paragraphs_a[i1 + offset] if offset < i2 - i1 else None
                paragraph_b = paragraphs_b[j1 + offset] if offset < j2 - j1 else None

                if paragraph_a is not None and paragraph_b is not None:
                    result.append(
                        {
                            "status": "changed",
                            "text_a": paragraph_a,
                            "text_b": paragraph_b,
                            "word_diff": _word_diff(paragraph_a, paragraph_b),
                        }
                    )
                elif paragraph_a is not None:
                    result.append({"status": "removed", "text_a": paragraph_a, "text_b": None, "word_diff": []})
                elif paragraph_b is not None:
                    result.append({"status": "added", "text_a": None, "text_b": paragraph_b, "word_diff": []})
        elif tag == "delete":
            for idx in range(i1, i2):
                result.append({"status": "removed", "text_a": paragraphs_a[idx], "text_b": None, "word_diff": []})
        elif tag == "insert":
            for idx in range(j1, j2):
                result.append({"status": "added", "text_a": None, "text_b": paragraphs_b[idx], "word_diff": []})

    return result
