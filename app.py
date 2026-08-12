"""Streamlit entry point for the Notice Comparison Tool."""

from __future__ import annotations

import hashlib
import html
from typing import Any

import streamlit as st

from src.diff_engine import compare_notices
from src.extractor import ExtractionError, extract_notice_fields, get_ocr_error_message, is_ocr_available
from src.text_diff import build_text_diff_summary, compare_full_text, render_word_diff_for_side


def _get_value_by_path(data: dict[str, Any] | None, path: str) -> Any:
    """Retrieve a nested value by dot-separated path."""
    if not data:
        return None

    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _flatten_fields(data: dict[str, Any] | None, prefix: str = "") -> list[dict[str, Any]]:
    """Return a flattened list of field paths and values for display, excluding metadata."""
    if not data:
        return []

    rows: list[dict[str, Any]] = []
    for key, value in data.items():
        if key == "metadata":
            continue
        field_name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            rows.extend(_flatten_fields(value, field_name))
        else:
            rows.append({"field": field_name, "value": value})
    return rows


def _render_word_diff(word_diff: list[str]) -> str:
    """Render a compact word-level diff using inline HTML highlighting."""
    if not word_diff:
        return ""

    rendered: list[str] = []
    for line in word_diff:
        if not line:
            continue
        prefix = line[:2]
        value = html.escape(line[2:])
        if prefix == "- ":
            rendered.append(f"<span style='text-decoration: line-through; color: #1a1a1a; background: #f8d7da; padding: 0 2px; border-radius: 2px;'>{value}</span>")
        elif prefix == "+ ":
            rendered.append(f"<span style='color: #1a1a1a; background: #d4edda; padding: 0 2px; border-radius: 2px;'>{value}</span>")
        elif prefix == "? ":
            continue
        else:
            rendered.append(f"<span style='color: #1a1a1a;'>{value}</span>")
    return " ".join(rendered)


def _render_full_text_comparison(notice_a: dict[str, Any] | None, notice_b: dict[str, Any] | None) -> None:
    """Render a document-level paragraph comparison beneath the structured field view."""
    raw_text_a = (notice_a or {}).get("metadata", {}).get("raw_text", "") if isinstance(notice_a, dict) else ""
    raw_text_b = (notice_b or {}).get("metadata", {}).get("raw_text", "") if isinstance(notice_b, dict) else ""

    if not raw_text_a and not raw_text_b:
        st.info("No raw text available for full-text comparison.")
        return

    diff_entries = compare_full_text(raw_text_a, raw_text_b)
    if not diff_entries:
        st.info("No paragraph-level text differences were detected.")
        return

    grouped = {
        "only_in_a": [entry for entry in diff_entries if entry.get("status") == "removed"],
        "only_in_b": [entry for entry in diff_entries if entry.get("status") == "added"],
        "changed": [entry for entry in diff_entries if entry.get("status") == "changed"],
        "unchanged": [entry for entry in diff_entries if entry.get("status") == "unchanged"],
    }

    st.subheader("Full Text Comparison")
    st.caption("Paragraph-level diff for narrative and clause-heavy documents. Structured field comparison remains above this section.")
    st.markdown(
        f"<div style='border:1px solid #d9d9d9; background:#f8f9fa; color:#1a1a1a; padding:12px; border-radius:6px; margin-bottom:12px;'>"
        f"<strong>{build_text_diff_summary(diff_entries)}</strong>"
        "</div>",
        unsafe_allow_html=True,
    )

    def render_only_in_a(entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        st.markdown("### Only in Document A")
        for entry in entries:
            text = entry.get("text_a")
            if not text:
                continue
            st.markdown(
                "<div style='border:1px solid #d1a2a7; background:#f8d7da; color:#1a1a1a; padding:10px; border-radius:6px; margin-bottom:8px;'>"
                "<strong>Document A</strong><br>"
                f"{html.escape(text)}"
                "</div>",
                unsafe_allow_html=True,
            )

    def render_only_in_b(entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        st.markdown("### Only in Document B")
        for entry in entries:
            text = entry.get("text_b")
            if not text:
                continue
            st.markdown(
                "<div style='border:1px solid #9ad0a8; background:#d4edda; color:#1a1a1a; padding:10px; border-radius:6px; margin-bottom:8px;'>"
                "<strong>Document B</strong><br>"
                f"{html.escape(text)}"
                "</div>",
                unsafe_allow_html=True,
            )

    def render_changed(entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        st.markdown("### Changed wording")
        for index, entry in enumerate(entries, start=1):
            left_col, right_col = st.columns(2)
            with left_col:
                st.markdown(
                    "<div style='border:1px solid #c7b36b; background:#fff3cd; color:#1a1a1a; padding:10px; border-radius:6px;'>"
                    "<strong>Document A</strong><br>"
                    f"{render_word_diff_for_side(entry.get('text_a') or '', entry.get('text_b') or '', 'a')}"
                    "</div>",
                    unsafe_allow_html=True,
                )
            with right_col:
                st.markdown(
                    "<div style='border:1px solid #9ad0a8; background:#d4edda; color:#1a1a1a; padding:10px; border-radius:6px;'>"
                    "<strong>Document B</strong><br>"
                    f"{render_word_diff_for_side(entry.get('text_a') or '', entry.get('text_b') or '', 'b')}"
                    "</div>",
                    unsafe_allow_html=True,
                )

    render_only_in_a(grouped["only_in_a"])
    render_only_in_b(grouped["only_in_b"])
    render_changed(grouped["changed"])

    if grouped["unchanged"]:
        with st.expander("Show unchanged sections", expanded=False):
            for index, entry in enumerate(grouped["unchanged"], start=1):
                st.markdown(
                    "<div style='border:1px solid #d9d9d9; background:#f5f5f5; color:#1a1a1a; padding:10px; border-radius:6px; margin-bottom:8px;'>"
                    f"<strong>Unchanged section {index}</strong><br>{html.escape(entry.get('text_a') or entry.get('text_b') or '')}"
                    "</div>",
                    unsafe_allow_html=True,
                )


def _render_field_rows(notice_a: dict[str, Any] | None, notice_b: dict[str, Any] | None, comparison_result: dict[str, Any] | None) -> None:
    """Render a side-by-side field comparison view for dynamic notice fields."""
    if comparison_result is None:
        return

    fields_a = {row["field"]: row["value"] for row in _flatten_fields(notice_a)}
    fields_b = {row["field"]: row["value"] for row in _flatten_fields(notice_b)}

    if not fields_a and not fields_b:
        st.info("No structured fields detected — see Full Text Comparison below.")
        return

    diff_entries = comparison_result.get("differences", [])
    if not diff_entries:
        st.info("No structured field differences were detected — see Full Text Comparison below.")
        return

    ordered_fields = sorted(
        set(fields_a) | set(fields_b),
        key=lambda field: (
            0 if field in fields_a and field in fields_b else 1,
            0 if field in fields_a else 1,
            field,
        ),
    )

    st.subheader("Comparison view")
    st.caption("Fields are displayed in a stable order, including any missing values from one notice.")

    for field in ordered_fields:
        entry = next((item for item in diff_entries if item.get("field") == field), None)
        status = entry["status"] if entry else "match"
        value_a = fields_a.get(field)
        value_b = fields_b.get(field)

        if status == "match":
            icon = "✅"
            color = "#d4edda"
            border = "#7aa27f"
        elif status == "missing":
            icon = "➖"
            color = "#f8d7da"
            border = "#c38b90"
        else:
            icon = "⚠️"
            color = "#fff3cd"
            border = "#c6b266"

        if value_a is None and field in fields_a:
            value_a_display = "Empty value"
        elif value_a is None:
            value_a_display = "Not present in Document A"
        else:
            value_a_display = value_a

        if value_b is None and field in fields_b:
            value_b_display = "Empty value"
        elif value_b is None:
            value_b_display = "Not present in Document B"
        else:
            value_b_display = value_b

        st.markdown(
            f"<div style='border:1px solid {border}; background:{color}; color:#1a1a1a; padding:10px; border-radius:6px; margin-bottom:8px;'>"
            f"<div><strong>{icon} {field}</strong></div>"
            f"<div style='margin-top:6px; color:#1a1a1a;'><span style='font-weight:600;'>Document A:</span> {value_a_display}</div>"
            f"<div style='color:#1a1a1a;'><span style='font-weight:600;'>Document B:</span> {value_b_display}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _extract_notice_from_upload(uploaded_file: Any) -> dict[str, Any]:
    """Extract and return notice fields from an uploaded PDF or JPEG file."""
    if uploaded_file is None:
        raise ValueError("No file uploaded.")

    file_type = uploaded_file.type or ""
    if file_type not in {"application/pdf", "image/jpeg", "image/jpg"}:
        raise ValueError("Please upload a PDF or JPEG file.")

    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    print(f"[hash-check] uploaded={uploaded_file.name} file_md5={file_hash}")

    with st.spinner("Extracting information..."):
        result = extract_notice_fields(file_bytes, file_type)

    raw_text = str(result.get("metadata", {}).get("raw_text", ""))
    raw_hash = hashlib.md5(raw_text.encode("utf-8", errors="ignore")).hexdigest()
    print(f"[hash-check] raw_text_md5={raw_hash}")
    return result


def main() -> None:
    """Render the comparison view and review workflow."""
    st.set_page_config(page_title="Notice Comparison Tool", page_icon="📋")
    st.title("Notice Comparison Tool")

    if not is_ocr_available():
        st.error(
            "OCR is unavailable in this environment. RapidOCR failed to initialize "
            f"during startup: {get_ocr_error_message()}. Uploads will not work until the OCR dependency is fixed."
        )
        st.stop()

    st.write("Upload two documents (PDF or JPEG) and compare them side by side.")

    st.session_state.setdefault("notice_a", None)
    st.session_state.setdefault("notice_b", None)
    st.session_state.setdefault("comparison_result", None)
    st.session_state.setdefault("review_decision", None)

    left_col, right_col = st.columns(2)
    with left_col:
        notice_a_file = st.file_uploader("Document A", key="notice_a_uploader", type=["pdf", "jpg", "jpeg"])
        if notice_a_file is not None:
            try:
                st.session_state["notice_a"] = _extract_notice_from_upload(notice_a_file)
                st.session_state["comparison_result"] = None
            except (ExtractionError, ValueError) as exc:
                st.error(str(exc))
                st.session_state["notice_a"] = None
                st.session_state["comparison_result"] = None

    with right_col:
        notice_b_file = st.file_uploader("Document B", key="notice_b_uploader", type=["pdf", "jpg", "jpeg"])
        if notice_b_file is not None:
            try:
                st.session_state["notice_b"] = _extract_notice_from_upload(notice_b_file)
                st.session_state["comparison_result"] = None
            except (ExtractionError, ValueError) as exc:
                st.error(str(exc))
                st.session_state["notice_b"] = None
                st.session_state["comparison_result"] = None
    # Advanced debug toggle to show temporary extraction details
    show_debug = st.checkbox("Advanced: show extraction details", value=False)

    if show_debug:
        if st.session_state["notice_a"] is not None:
            with st.expander("Document A raw output", expanded=False):
                st.subheader("Raw extracted text")
                st.text_area(
                    "",
                    st.session_state["notice_a"].get("metadata", {}).get("raw_text", ""),
                    height=240,
                    key="debug_raw_text_a",
                )
                st.subheader("Parsed field dict")
                st.json({
                    key: value
                    for key, value in st.session_state["notice_a"].items()
                    if key != "metadata"
                })

        if st.session_state["notice_b"] is not None:
            with st.expander("Document B raw output", expanded=False):
                st.subheader("Raw extracted text")
                st.text_area(
                    "",
                    st.session_state["notice_b"].get("metadata", {}).get("raw_text", ""),
                    height=240,
                    key="debug_raw_text_b",
                )
                st.subheader("Parsed field dict")
                st.json({
                    key: value
                    for key, value in st.session_state["notice_b"].items()
                    if key != "metadata"
                })

    can_run_comparison = st.session_state["notice_a"] is not None and st.session_state["notice_b"] is not None

    if st.button("Run comparison", disabled=not can_run_comparison):
        st.session_state["comparison_result"] = compare_notices(
            st.session_state["notice_a"],
            st.session_state["notice_b"],
        )
        st.session_state["review_decision"] = None
        st.success("Comparison generated.")

    if st.session_state["comparison_result"] is not None:
        result = st.session_state["comparison_result"]
        notice_a = st.session_state.get("notice_a")
        notice_b = st.session_state.get("notice_b")

        raw_text_a = (notice_a or {}).get("metadata", {}).get("raw_text", "") if isinstance(notice_a, dict) else ""
        raw_text_b = (notice_b or {}).get("metadata", {}).get("raw_text", "") if isinstance(notice_b, dict) else ""
        text_diff_entries = compare_full_text(raw_text_a, raw_text_b)
        text_diff_count = sum(1 for entry in text_diff_entries if entry.get("status") in {"changed", "added", "removed"})
        field_diff_count = sum(1 for entry in result.get("differences", []) if entry.get("status") in {"mismatch", "missing"})

        text_summary = build_text_diff_summary(text_diff_entries)
        if field_diff_count == 0 and text_diff_count == 0:
            summary = "No differences detected."
        elif field_diff_count == 0:
            summary = text_summary
        elif text_diff_count == 0:
            summary = f"Detected {field_diff_count} field difference(s)."
        else:
            summary = f"Detected {field_diff_count} field difference(s). {text_summary}"

        st.subheader("Result summary")
        st.write(summary)

        _render_field_rows(st.session_state["notice_a"], st.session_state["notice_b"], result)
        _render_full_text_comparison(st.session_state["notice_a"], st.session_state["notice_b"])

        st.subheader("Confirm decision")
        confirm_col_1, confirm_col_2, confirm_col_3 = st.columns(3)
        with confirm_col_1:
            if st.button("Confirm Match"):
                st.session_state["review_decision"] = "match"
                st.success("Marked as match.")
        with confirm_col_2:
            if st.button("Confirm Mismatch"):
                st.session_state["review_decision"] = "mismatch"
                st.success("Marked as mismatch.")
        with confirm_col_3:
            if st.button("Need More Review"):
                st.session_state["review_decision"] = "needs_review"
                st.info("Marked for further review.")

        if st.session_state["review_decision"] is not None:
            st.caption(f"Current review decision: {st.session_state['review_decision']}")


if __name__ == "__main__":
    main()
