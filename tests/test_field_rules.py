from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.field_rules import parse_notice_fields


def test_generic_label_value_parsing_variants():
    text = """Notice ID: N-1001
Recipient - Jane Doe
Amount Due: $1,250.00
Due Date: 2026-01-15
"""
    parsed = parse_notice_fields(text)

    assert parsed["notice id"] == "N-1001"
    assert parsed["recipient"] == "Jane Doe"
    assert parsed["amount due"] == "$1,250.00"
    assert parsed["due date"] == "2026-01-15"


def test_generic_label_value_parsing_with_ocr_noise():
    text = """N0T1CE_ID:: N-2022
AM0UNT__DUE--- $2,500.00
R3cipi3nt   =   Jane   Doe
"""
    parsed = parse_notice_fields(text)

    assert parsed["n0t1ce id"] == "N-2022"
    assert parsed["am0unt due"] == "$2,500.00"
    assert parsed["r3cipi3nt"] == "Jane Doe"


def test_non_matching_lines_are_ignored():
    text = """----
Page 4 of 8
NOTICE OF DEFAULT
This is a narrative sentence with no label/value pairs.
Amount Due: $30.00
"""
    parsed = parse_notice_fields(text)

    assert parsed == {"amount due": "$30.00"}


def test_normalization_standardizes_underscores_and_spaces():
    text = """notice_id: N-3003
amount_due = $123.45
Notice ID: N-4004
"""
    parsed = parse_notice_fields(text)

    assert parsed["notice id"] == "N-4004"
    assert parsed["amount due"] == "$123.45"


def test_label_variants_with_different_casing_spacing_and_wording_match_same_notice():
    left = """Notice ID: N-1001
Recipient - Jane Doe
Amount Due : $1,250.00
Due Date = 2026-01-15
"""
    right = """notice_id  N-1001
recipient    Jane Doe
amount_due  $1,250.00
due_date=2026-01-15
"""

    parsed_left = parse_notice_fields(left)
    parsed_right = parse_notice_fields(right)

    assert parsed_left == parsed_right == {
        "notice id": "N-1001",
        "recipient": "Jane Doe",
        "amount due": "$1,250.00",
        "due date": "2026-01-15",
    }


def test_unstructured_text_returns_empty_dict_instead_of_crashing():
    text = """This is a plain-language notice with no label/value pairs.
There are no field names here, just narrative text.
The document is informational only and should not parse as structured data.
"""

    parsed = parse_notice_fields(text)

    assert parsed == {}
