"""Unit tests for testcase_generator (LLM call mocked, no live model)."""

from unittest import mock

from src import llm
from src.testcase_generator import (
    generate_testcases,
    generate_testcases_for_technique,
    merge_technique_testcases,
)

REQUIREMENT = """
{
  "module_name": "Login",
  "input_fields": ["Username", "Password"],
  "business_rules": ["Username mandatory", "Password mandatory"],
  "workflow": ["Enter Username", "Enter Password", "Click Login", "Navigate Dashboard"]
}
"""

TECHNIQUES = """
{
  "Functional Testing": true,
  "Positive Testing": true,
  "Negative Testing": true
}
"""


def _mock_chat_reply(text):
    return mock.patch.object(llm, "chat", return_value=text)


def test_generate_testcases_passes_both_inputs():
    expected = '[{"S.No": 1}]'

    with _mock_chat_reply(expected) as mocked_chat:
        result = generate_testcases(REQUIREMENT, TECHNIQUES)

    assert result == expected
    prompt = mocked_chat.call_args.args[1]
    assert "Login" in prompt
    assert "Positive Testing" in prompt
    assert mocked_chat.call_args.kwargs["json_mode"] is True
    assert mocked_chat.call_args.kwargs["system"]
    assert "ARRAY" in mocked_chat.call_args.kwargs["system"]


def test_generate_testcases_gwt_uses_gwt_prompt():
    with _mock_chat_reply("[]") as mocked_chat:
        generate_testcases(REQUIREMENT, TECHNIQUES, test_case_format="GWT")

    prompt = mocked_chat.call_args.args[1]
    assert "Given" in prompt or "When" in prompt or "Then" in prompt


def test_generate_testcases_retry_hint_appended():
    with _mock_chat_reply("[]") as mocked_chat:
        generate_testcases(REQUIREMENT, TECHNIQUES, retry_hint="Your previous response was invalid JSON.")

    prompt = mocked_chat.call_args.args[1]
    assert "invalid JSON" in prompt


def test_generate_for_technique_focuses_single_technique():
    with _mock_chat_reply('[{"S.No": 1}]') as mocked_chat:
        result = generate_testcases_for_technique(
            REQUIREMENT, "Boundary Value Analysis"
        )

    assert result == '[{"S.No": 1}]'

    prompt = mocked_chat.call_args.args[1]
    assert "Boundary Value Analysis" in prompt
    assert "Apply ONLY this testing technique" in prompt
    assert "EXACTLY" in prompt
    assert "SKELETON TO FILL" in prompt
    assert mocked_chat.call_args.kwargs["json_mode"] is True
    assert "ARRAY" in mocked_chat.call_args.kwargs["system"]


def test_merge_technique_testcases_flattens_tags_and_renumbers():
    functional = [
        {"S.No": 1, "Title of Test Case": "Login works"},
        {"S.No": 2, "Title of Test Case": "Logout works"},
    ]
    negative = [
        {"S.No": 1, "Title of Test Case": "Wrong password rejected"},
    ]

    merged = merge_technique_testcases(
        [("Functional Testing", functional), ("Negative Testing", negative)]
    )

    assert len(merged) == 3
    assert merged[0]["Testing Technique"] == "Functional Testing"
    assert merged[2]["Testing Technique"] == "Negative Testing"
    assert [case["S.No"] for case in merged] == [1, 2, 3]

def test_merge_handles_single_dict_and_bad_rows():
    merged = merge_technique_testcases(
        [
            ("UI Validation", {"S.No": 1, "Title of Test Case": "Button visible"}),
            ("API Validation", [42, {"S.No": 2, "Title of Test Case": "API ok"}]),
        ]
    )

    assert len(merged) == 2
    assert merged[0]["Title of Test Case"] == "Button visible"
    assert merged[0]["S.No"] == 1
    assert merged[1]["Title of Test Case"] == "API ok"
    assert merged[1]["S.No"] == 2


def test_short_reply_triggers_topup_and_dedupes():
    short = '[{"S.No": 1, "Title of Test Case": "Repeat me"}]'
    full = (
        '[{"S.No": 1, "Title of Test Case": "Repeat me"},'
        '{"S.No": 2, "Title of Test Case": "New case 1"},'
        '{"S.No": 3, "Title of Test Case": "New case 2"},'
        '{"S.No": 4, "Title of Test Case": "New case 3"}]'
    )

    with mock.patch.object(llm, "chat", side_effect=[short, full]) as mocked_chat:
        result = generate_testcases_for_technique(REQUIREMENT, "Negative Testing")

    import json as _json

    rows = _json.loads(result)
    assert len(rows) == 4
    assert [r["Title of Test Case"] for r in rows] == [
        "Repeat me",
        "New case 1",
        "New case 2",
        "New case 3",
    ]
    assert mocked_chat.call_count == 2
    assert "do NOT repeat" in mocked_chat.call_args.args[1]
