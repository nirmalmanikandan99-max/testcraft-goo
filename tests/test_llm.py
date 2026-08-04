"""
Unit tests for the LLM provider layer (src/llm.py).

The online providers are tested with a mocked httpx transport, so no
real API key or network is needed. The Ollama branch is tested by
stubbing the internal call, since the app may run without Ollama.
"""

import httpx
from unittest import mock

from src import llm
from src.llm import LLMConfig, LLMError


def _fake_response(payload, status=200):
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("POST", "http://fake"),
    )


def test_gemini_chat_posts_openai_shape():
    with mock.patch.object(
        llm.httpx,
        "post",
        return_value=_fake_response({"choices": [{"message": {"content": "hello"}}]}),
    ) as mocked_post:
        config = LLMConfig(provider="gemini", api_key="secret", model="gemini-2.5-flash")
        result = llm.chat(config, "Hello", temperature=0.1, num_predict=300)

    assert result == "hello"

    args, kwargs = mocked_post.call_args
    assert "generativelanguage.googleapis.com" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    assert kwargs["json"]["model"] == "gemini-2.5-flash"
    assert kwargs["json"]["temperature"] == 0.1
    assert kwargs["json"]["max_tokens"] == 300
    assert kwargs["json"]["messages"][0]["content"] == "Hello"


def test_groq_chat_uses_groq_base_url():
    with mock.patch.object(
        llm.httpx,
        "post",
        return_value=_fake_response({"choices": [{"message": {"content": "ok"}}]}),
    ) as mocked_post:
        config = LLMConfig(provider="groq", api_key="k")
        llm.chat(config, "Hi", num_predict=100)

    args, kwargs = mocked_post.call_args
    assert args[0].startswith("https://api.groq.com/openai/v1")
    assert kwargs["json"]["model"] == "llama-3.3-70b-versatile"


def test_missing_api_key_raises_friendly_error():
    try:
        llm.chat(LLMConfig(provider="gemini"), "Hi")
    except LLMError as exc:
        assert "Missing API key" in str(exc)
    else:
        raise AssertionError("Expected LLMError")


def test_unauthorized_raises_friendly_error():
    with mock.patch.object(
        llm.httpx,
        "post",
        return_value=_fake_response({"error": "nope"}, status=401),
    ):
        try:
            llm.chat(LLMConfig(provider="gemini", api_key="bad"), "Hi")
        except LLMError as exc:
            assert "401" in str(exc)
        else:
            raise AssertionError("Expected LLMError")


def test_rate_limit_raises_friendly_error():
    with mock.patch.object(
        llm.httpx,
        "post",
        return_value=_fake_response({"error": "slow down"}, status=429),
    ):
        try:
            llm.chat(LLMConfig(provider="groq", api_key="k"), "Hi")
        except LLMError as exc:
            assert "429" in str(exc)
        else:
            raise AssertionError("Expected LLMError")


def test_connect_error_raises_friendly_error():
    with mock.patch.object(
        llm.httpx,
        "post",
        side_effect=httpx.ConnectError("boom"),
    ):
        try:
            llm.chat(LLMConfig(provider="gemini", api_key="k"), "Hi")
        except LLMError as exc:
            assert "internet connection" in str(exc)
        else:
            raise AssertionError("Expected LLMError")


def test_ollama_routes_to_local_call():
    with mock.patch.object(llm, "_call_ollama", return_value="local reply") as mocked:
        result = llm.chat(LLMConfig(), "Hi")

    assert result == "local reply"
    mocked.assert_called_once()


def test_default_models_per_provider():
    assert LLMConfig(provider="gemini").effective_model() == "gemini-2.5-flash"
    assert LLMConfig(provider="groq").effective_model() == "llama-3.3-70b-versatile"
    assert LLMConfig().effective_model() == "qwen2.5:7b"
    assert LLMConfig(provider="gemini", model="custom").effective_model() == "custom"


def test_unknown_online_provider_raises():
    try:
        llm.chat(LLMConfig(provider="mars", api_key="k"), "Hi")
    except LLMError as exc:
        assert "mars" in str(exc)
    else:
        raise AssertionError("Expected LLMError")
