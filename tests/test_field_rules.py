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
