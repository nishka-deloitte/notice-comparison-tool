"""Comparison logic for notice extraction results."""

from __future__ import annotations

from typing import Any


def normalize_value(value: Any) -> Any:
    """Normalize a value before comparison."""
    if isinstance(value, str):
        return value.strip().lower()
    return value


def _compare_values(value_a: Any, value_b: Any, field: str) -> dict[str, Any]:
    """Compare two values and return a field diff entry."""
    if value_a is None and value_b is None:
        return {"field": field, "status": "match", "value_a": None, "value_b": None}

    if value_a is None:
        return {"field": field, "status": "missing", "missing_in": "left", "value_a": None, "value_b": value_b}

    if value_b is None:
        return {"field": field, "status": "missing", "missing_in": "right", "value_a": value_a, "value_b": None}

    if type(value_a) is not type(value_b):
        return {"field": field, "status": "mismatch", "value_a": value_a, "value_b": value_b}

    if isinstance(value_a, dict):
        return {"field": field, "status": "match", "value_a": value_a, "value_b": value_b}

    if isinstance(value_a, list):
        return {"field": field, "status": "match" if value_a == value_b else "mismatch", "value_a": value_a, "value_b": value_b}

    normalized_a = normalize_value(value_a)
    normalized_b = normalize_value(value_b)
    status = "match" if normalized_a == normalized_b else "mismatch"
    return {"field": field, "status": status, "value_a": value_a, "value_b": value_b}


def _compare_nested(left: dict[str, Any], right: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    """Recursively compare nested dictionaries and return diff entries."""
    differences: list[dict[str, Any]] = []
    all_keys = sorted(set(left.keys()) | set(right.keys()))

    for key in all_keys:
        field_name = f"{prefix}.{key}" if prefix else key
        left_value = left.get(key)
        right_value = right.get(key)

        if key not in left:
            differences.append({
                "field": field_name,
                "status": "missing",
                "missing_in": "left",
                "value_a": None,
                "value_b": right_value,
            })
            continue

        if key not in right:
            differences.append({
                "field": field_name,
                "status": "missing",
                "missing_in": "right",
                "value_a": left_value,
                "value_b": None,
            })
            continue

        if isinstance(left_value, dict) and isinstance(right_value, dict):
            differences.extend(_compare_nested(left_value, right_value, field_name))
            continue

        differences.append(_compare_values(left_value, right_value, field_name))

    return differences


def compare_notices(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Compare two notice extraction results using the union of their parsed keys."""
    left_for_compare = {k: v for k, v in left.items() if k != "metadata" and not str(k).startswith("metadata.")}
    right_for_compare = {k: v for k, v in right.items() if k != "metadata" and not str(k).startswith("metadata.")}

    differences = _compare_nested(left_for_compare, right_for_compare)
    mismatch_count = sum(1 for entry in differences if entry["status"] == "mismatch")
    missing_count = sum(1 for entry in differences if entry["status"] == "missing")

    if mismatch_count == 0 and missing_count == 0:
        status = "match"
        summary = "No differences detected."
        label = "match"
    elif mismatch_count > 0:
        status = "mismatch"
        summary = f"Detected {mismatch_count} mismatched field(s)."
        label = "mismatch"
    else:
        status = "mismatch"
        summary = f"Detected {missing_count} missing field(s)."
        label = "needs_review"

    return {
        "status": status,
        "summary": summary,
        "differences": differences,
        "classification": {
            "label": label,
            "confidence": 0.9 if status == "mismatch" else 1.0,
            "reason": "Field-level comparison completed.",
        },
    }
