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
    ), mock.patch.object(llm.time, "sleep") as mocked_sleep:
        try:
            llm.chat(LLMConfig(provider="groq", api_key="k"), "Hi")
        except LLMError as exc:
            assert "429" in str(exc)
            assert mocked_sleep.call_count == 2  # backed off twice
        else:
            raise AssertionError("Expected LLMError")


def test_429_retries_until_success():
    # Two 429s, then a good response: backoff must wait and succeed.
    responses = [
        _fake_response({"error": "slow down"}, status=429),
        _fake_response({"error": "slow down"}, status=429),
        _fake_response({"choices": [{"message": {"content": "ok"}}]}),
    ]

    with mock.patch.object(
        llm.httpx, "post", side_effect=responses
    ) as mocked_post, mock.patch.object(llm.time, "sleep"):
        result = llm.chat(LLMConfig(provider="gemini", api_key="k"), "Hi")

    assert result == "ok"
    assert mocked_post.call_count == 3


def test_429_respects_retry_after_header():
    response = httpx.Response(
        429,
        json={"error": "slow down"},
        headers={"retry-after": "3"},
        request=httpx.Request("POST", "http://fake"),
    )

    with mock.patch.object(
        llm.httpx, "post", side_effect=[response, _fake_response({"choices": [{"message": {"content": "ok"}}]})]
    ) as mocked_post, mock.patch.object(llm.time, "sleep") as mocked_sleep:
        result = llm.chat(LLMConfig(provider="groq", api_key="k"), "Hi")

    assert result == "ok"
    assert mocked_sleep.call_args.args[0] == 3.0


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
    assert LLMConfig(provider="gemini").effective_model() == "gemini-3-flash"
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


def test_404_falls_back_to_next_model():
    # Configured model 404s -> provider retries the fallback list, succeeds.
    responses = [
        _fake_response({"error": "not found"}, status=404),
        _fake_response({"choices": [{"message": {"content": "ok"}}]}),
    ]

    with mock.patch.object(llm.httpx, "post", side_effect=responses) as mocked_post:
        config = LLMConfig(provider="gemini", api_key="k", model="stale-model")
        result = llm.chat(config, "Hi")

    assert result == "ok"
    body = mocked_post.call_args_list[-1].kwargs["json"]
    assert body["model"] != "stale-model"  # used a fallback model


def test_all_models_404_raises_friendly_error():
    with mock.patch.object(
        llm.httpx,
        "post",
        return_value=_fake_response({"error": "nope"}, status=404),
    ):
        try:
            llm.chat(LLMConfig(provider="gemini", api_key="k", model="stale-model"), "Hi")
        except LLMError as exc:
            assert "Model not found (404)" in str(exc)
            assert "stale-model" in str(exc)
        else:
            raise AssertionError("Expected LLMError")


def test_list_models_returns_ids():
    with mock.patch.object(
        llm.httpx,
        "get",
        return_value=_fake_response(
            {"data": [{"id": "gemini-3-flash"}, {"id": "gemini-2.5-flash"}]}
        ),
    ) as mocked_get:
        ids = llm.list_models(LLMConfig(provider="gemini", api_key="k"))

    assert ids == ["gemini-2.5-flash", "gemini-3-flash"]
    assert "Bearer k" in mocked_get.call_args.kwargs["headers"]["Authorization"]


def test_list_models_empty_without_key():
    assert llm.list_models(LLMConfig(provider="gemini")) == []
    assert llm.list_models(LLMConfig()) == []


def test_chat_prepends_system_message():
    with mock.patch.object(
        llm.httpx, "post", return_value=_fake_response({"choices": [{"message": {"content": "ok"}}]})
    ) as mocked_post:
        llm.chat(
            LLMConfig(provider="gemini", api_key="k"),
            "Make JSON",
            system="You only output JSON.",
        )

    messages = mocked_post.call_args.kwargs["json"]["messages"]
    assert messages[0] == {"role": "system", "content": "You only output JSON."}
    assert messages[1] == {"role": "user", "content": "Make JSON"}


def test_chat_without_system_has_only_user_message():
    with mock.patch.object(
        llm.httpx, "post", return_value=_fake_response({"choices": [{"message": {"content": "ok"}}]})
    ) as mocked_post:
        llm.chat(LLMConfig(provider="groq", api_key="k"), "Hi")

    messages = mocked_post.call_args.kwargs["json"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


def test_json_mode_sets_response_format():
    with mock.patch.object(
        llm.httpx, "post", return_value=_fake_response({"choices": [{"message": {"content": "{}"}}]})
    ) as mocked_post:
        llm.chat(
            LLMConfig(provider="gemini", api_key="k"),
            "Return JSON",
            json_mode=True,
        )

    body = mocked_post.call_args.kwargs["json"]
    assert body["response_format"] == {"type": "json_object"}


def test_no_json_mode_omits_response_format():
    with mock.patch.object(
        llm.httpx, "post", return_value=_fake_response({"choices": [{"message": {"content": "ok"}}]})
    ) as mocked_post:
        llm.chat(LLMConfig(provider="gemini", api_key="k"), "Hi")

    body = mocked_post.call_args.kwargs["json"]
    assert "response_format" not in body
