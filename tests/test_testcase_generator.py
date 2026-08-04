"""Unit tests for testcase_generator (LLM call mocked, no live model)."""

from unittest import mock

from src import llm
from src.testcase_generator import generate_testcases

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
