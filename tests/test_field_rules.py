from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.field_rules import parse_notice_fields


def test_garbled_json_like_fields():
    text = '"notice_id": "N-1001", "issue_date" 2026-01-15\', "recipient"= \'Jane Doe\''
    parsed, unparsed, json_err = parse_notice_fields(text)
    assert parsed.get("notice_id") == "N-1001"
    assert parsed.get("due_date") == "2026-01-15"
    assert parsed.get("recipient") == "Jane Doe"
    assert json_err is None


def test_variations_with_spaces_and_separators():
    text = 'notice id": "N-1001" "issue_date": "2026-01-15", "recipient": \'Jane Doe\''
    parsed, unparsed, json_err = parse_notice_fields(text)
    assert parsed.get("notice_id") == "N-1001"
    assert parsed.get("due_date") == "2026-01-15"
    assert parsed.get("recipient") == "Jane Doe"
    assert json_err is None


def test_missing_separators_and_split_lines():
    # Missing explicit separators and values split across lines
    text = 'notice_id "N-2002"\nrecipient\n= "Alice Smith", amount due $1,234.00.\nissue_date - 2026-02-02'
    parsed, unparsed, json_err = parse_notice_fields(text)
    assert parsed.get("notice_id") == "N-2002"
    assert parsed.get("recipient") == "Alice Smith"
    assert parsed.get("amount_due") == 1234
    assert parsed.get("due_date") == "2026-02-02"
    assert json_err is None


def test_extra_punctuation_and_noise():
    # Extra punctuation and trailing characters
    text = '"notice id" : "N-3003"; "issue_date": "2026-03-03".. "recipient": "Bob, Jr.", "amount_due": "$2,500.00,,"'
    parsed, unparsed, json_err = parse_notice_fields(text)
    assert parsed.get("notice_id") == "N-3003"
    assert parsed.get("recipient") == "Bob, Jr."
    assert parsed.get("amount_due") == 2500
    assert parsed.get("due_date") == "2026-03-03"
    assert json_err is None
