"""Unit tests for json_validator.validate_json."""

from src.json_validator import validate_json


def test_plain_json_array_parses():
    sample = (
        '[{"S.No": 1, "Title of Test Case": "Verify Login", '
        '"Testing Technique": "Functional Testing"}]'
    )
    assert validate_json(sample) is not None


def test_markdown_fenced_json_parses():
    fenced = '```json\n{"module_name": "Login"}\n```'
    result = validate_json(fenced)
    assert result == {"module_name": "Login"}


def test_json_with_surrounding_text_parses():
    wrapped = 'Here is the result:\n{"workflow": ["Enter Username", "Login"]}\nDone.'
    result = validate_json(wrapped)
    assert result == {"workflow": ["Enter Username", "Login"]}


def test_invalid_input_returns_none():
    assert validate_json("Half-day only for single-day leave.") is None
    assert validate_json("...") is None
    assert validate_json("") is None
    assert validate_json("not json at all") is None


def test_truncated_json_returns_none():
    truncated = '{"module_name": "Login", "business_rules": ["a", "b'
    assert validate_json(truncated) is None
