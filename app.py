"""Streamlit entry point for the Notice Comparison Tool."""

from __future__ import annotations

from typing import Any

import streamlit as st

from src.diff_engine import compare_notices
from src.extractor import ExtractionError, extract_notice_fields


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
    """Return a flattened list of field paths and values for display."""
    if not data:
        return []

    rows: list[dict[str, Any]] = []
    for key, value in data.items():
        field_name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            rows.extend(_flatten_fields(value, field_name))
        else:
            rows.append({"field": field_name, "value": value})
    return rows


def _render_field_rows(notice_a: dict[str, Any] | None, notice_b: dict[str, Any] | None, comparison_result: dict[str, Any] | None) -> None:
    """Render a side-by-side field comparison view."""
    if comparison_result is None:
        return

    diff_map = {entry["field"]: entry for entry in comparison_result.get("differences", [])}
    fields_a = {row["field"]: row["value"] for row in _flatten_fields(notice_a)}
    fields_b = {row["field"]: row["value"] for row in _flatten_fields(notice_b)}
    all_fields = sorted(set(fields_a) | set(fields_b))

    st.subheader("Comparison view")
    st.caption("Fields with status indicators are highlighted for review.")

    for field in all_fields:
        entry = diff_map.get(field)
        status = entry["status"] if entry else "match"
        value_a = fields_a.get(field)
        value_b = fields_b.get(field)

        if status == "match":
            icon = "✅"
            color = "#f7f7f7"
            border = "#bdbdbd"
        elif status == "missing":
            icon = "➖"
            color = "#fff4f4"
            border = "#d9534f"
        else:
            icon = "⚠️"
            color = "#fff8e1"
            border = "#f0ad4e"

        st.markdown(
            f"<div style='border:1px solid {border}; background:{color}; color:#1a1a1a; padding:10px; border-radius:6px; margin-bottom:8px;'>"
            f"<div><strong>{icon} {field}</strong></div>"
            f"<div style='margin-top:6px; color:#1a1a1a;'><span style='font-weight:600;'>Notice A:</span> {value_a if value_a is not None else 'Not present'}</div>"
            f"<div style='color:#1a1a1a;'><span style='font-weight:600;'>Notice B:</span> {value_b if value_b is not None else 'Not present'}</div>"
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

    with st.spinner("Extracting information..."):
        return extract_notice_fields(uploaded_file.getvalue(), file_type)


def main() -> None:
    """Render the comparison view and review workflow."""
    st.set_page_config(page_title="Notice Comparison Tool", page_icon="📋")
    st.title("Notice Comparison Tool")

    st.write("Upload two notice documents (PDF or JPEG) and compare them side by side.")

    st.session_state.setdefault("notice_a", None)
    st.session_state.setdefault("notice_b", None)
    st.session_state.setdefault("comparison_result", None)
    st.session_state.setdefault("review_decision", None)

    left_col, right_col = st.columns(2)
    with left_col:
        notice_a_file = st.file_uploader("Notice A", type=["pdf", "jpg", "jpeg"])
        if notice_a_file is not None:
            try:
                st.session_state["notice_a"] = _extract_notice_from_upload(notice_a_file)
            except (ExtractionError, ValueError) as exc:
                st.error(str(exc))
                st.session_state["notice_a"] = None

    with right_col:
        notice_b_file = st.file_uploader("Notice B", type=["pdf", "jpg", "jpeg"])
        if notice_b_file is not None:
            try:
                st.session_state["notice_b"] = _extract_notice_from_upload(notice_b_file)
            except (ExtractionError, ValueError) as exc:
                st.error(str(exc))
                st.session_state["notice_b"] = None
    # Advanced debug toggle to show temporary extraction details
    show_debug = st.checkbox("Advanced: show extraction details", value=False)

    if show_debug:
        if st.session_state["notice_a"] is not None:
            with st.expander("Debug: Notice A raw output", expanded=False):
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
            with st.expander("Debug: Notice B raw output", expanded=False):
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
        st.subheader("Result summary")
        st.write(result.get("summary", "No summary available."))

        _render_field_rows(st.session_state["notice_a"], st.session_state["notice_b"], result)

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
