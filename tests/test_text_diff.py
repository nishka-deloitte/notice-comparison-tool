from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.text_diff import build_text_diff_summary, compare_full_text, group_text_diff_entries


def test_compare_full_text_identical_text() -> None:
    text_a = "Paragraph one.\n\nParagraph two."
    text_b = "Paragraph one.\n\nParagraph two."

    result = compare_full_text(text_a, text_b)

    assert result == [
        {"status": "unchanged", "text_a": "Paragraph one.", "text_b": "Paragraph one.", "word_diff": []},
        {"status": "unchanged", "text_a": "Paragraph two.", "text_b": "Paragraph two.", "word_diff": []},
    ]


def test_compare_full_text_detects_changed_word() -> None:
    text_a = "The tenant pays rent on the first day."
    text_b = "The tenant pays rent on the fifth day."

    result = compare_full_text(text_a, text_b)

    assert len(result) == 1
    assert result[0]["status"] == "changed"
    assert result[0]["text_a"] == "The tenant pays rent on the first day."
    assert result[0]["text_b"] == "The tenant pays rent on the fifth day."
    assert result[0]["word_diff"]


def test_compare_full_text_handles_added_paragraph() -> None:
    text_a = "First paragraph."
    text_b = "First paragraph.\n\nSecond paragraph added."

    result = compare_full_text(text_a, text_b)

    assert [entry["status"] for entry in result] == ["unchanged", "added"]
    assert result[0]["text_a"] == "First paragraph."
    assert result[1]["text_b"] == "Second paragraph added."
    assert result[1]["text_a"] is None


def test_compare_full_text_handles_removed_paragraph() -> None:
    text_a = "First paragraph.\n\nSecond paragraph removed."
    text_b = "First paragraph."

    result = compare_full_text(text_a, text_b)

    assert [entry["status"] for entry in result] == ["unchanged", "removed"]
    assert result[0]["text_a"] == "First paragraph."
    assert result[1]["text_a"] == "Second paragraph removed."
    assert result[1]["text_b"] is None


def test_compare_full_text_handles_completely_different_text() -> None:
    text_a = "Alpha beta gamma."
    text_b = "Delta epsilon zeta."

    result = compare_full_text(text_a, text_b)

    assert len(result) == 1
    assert result[0]["status"] == "changed"
    assert "Alpha" in result[0]["text_a"]
    assert "Delta" in result[0]["text_b"]
    assert result[0]["word_diff"]


def test_compare_full_text_handles_long_lease_paragraphs() -> None:
    text_a = (
        "The Tenant shall pay all rent due under this Lease in equal monthly installments of $2,500.00, "
        "payable in advance on the first day of each calendar month, and any late charge shall accrue at the rate "
        "of one and one-half percent (1.5%) per month on any unpaid balance remaining past the due date."
    )
    text_b = (
        "The Tenant shall pay all rent due under this Lease in equal monthly installments of $2,500.00, "
        "payable in advance on the fifth day of each calendar month, and any late charge shall accrue at the rate "
        "of one and one-half percent (1.5%) per month on any unpaid balance remaining past the due date after notice."
    )

    result = compare_full_text(text_a, text_b)

    assert len(result) == 1
    assert result[0]["status"] == "changed"
    assert result[0]["text_a"] == text_a
    assert result[0]["text_b"] == text_b
    assert 10 <= len(result[0]["word_diff"]) <= 80


def test_compare_full_text_handles_ocr_noise_in_prose() -> None:
    text_a = (
        "The Landlord shall provide reasonable notice before entering the Premises, and shall not disturb the Tenant's quiet enjoyment "
        "of the demised premises during the Term."
    )
    text_b = (
        "Th3 Landlord shal1 provide reasonable notice before entering the Premises, and shal1 not disturb the Tenant's quiet enjoyment "
        "of the demised premises during the Term."
    )

    result = compare_full_text(text_a, text_b)

    assert len(result) == 1
    assert result[0]["status"] == "changed"
    assert result[0]["word_diff"]
    assert len(result[0]["word_diff"]) < 100


def test_compare_full_text_marks_document_a_only_as_removed_and_document_b_only_as_added() -> None:
    text_a = "Shared paragraph.\n\nDocument A only paragraph."
    text_b = "Shared paragraph."

    result_a_only = compare_full_text(text_a, text_b)
    assert [entry["status"] for entry in result_a_only] == ["unchanged", "removed"]
    assert result_a_only[1]["text_a"] == "Document A only paragraph."
    assert result_a_only[1]["text_b"] is None

    text_c = "Shared paragraph."
    text_d = "Shared paragraph.\n\nDocument B only paragraph."

    result_b_only = compare_full_text(text_c, text_d)
    assert [entry["status"] for entry in result_b_only] == ["unchanged", "added"]
    assert result_b_only[1]["text_a"] is None
    assert result_b_only[1]["text_b"] == "Document B only paragraph."


def test_build_text_diff_summary_counts_only_in_each_document_and_changed_sections() -> None:
    entries = [
        {"status": "removed", "text_a": "A-only text"},
        {"status": "added", "text_b": "B-only text"},
        {"status": "changed", "text_a": "Old wording", "text_b": "New wording"},
        {"status": "changed", "text_a": "Another old", "text_b": "Another new"},
        {"status": "unchanged", "text_a": "Same", "text_b": "Same"},
    ]

    summary = build_text_diff_summary(entries)

    assert summary == (
        "Document A has 1 sections/lines not found in Document B, and Document B has 1 sections/lines not found in Document A. "
        "2 sections have minor wording differences."
    )
    grouped = group_text_diff_entries(entries)
    assert grouped["only_in_a"][0]["text_a"] == "A-only text"
    assert grouped["only_in_b"][0]["text_b"] == "B-only text"
    assert len(grouped["changed"]) == 2
