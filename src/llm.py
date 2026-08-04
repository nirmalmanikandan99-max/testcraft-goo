"""
Unified LLM provider layer.

Lets every pipeline stage switch between:

  - "ollama" : local model (original behaviour, no API key, offline)
  - "gemini" : Google AI Studio free tier (BYOK — user pastes their own key)
  - "groq"   : Groq free tier (BYOK)

Gemini and Groq both expose OpenAI-compatible chat endpoints, so a single
httpx call shape covers both. httpx is already a project dependency.

API keys are only ever passed in memory (per-session) — never persisted.
"""

import httpx

from src.config import (
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GROQ_BASE_URL,
    GROQ_MODEL,
    MODEL_NAME,
)

DEFAULT_TIMEOUT = 180.0


class LLMError(Exception):
    """Raised when a provider call fails (auth, network, rate limit, ...)."""


class LLMConfig:
    """Provider selection + BYOK credentials. Plain object, JSON-able."""

    def __init__(self, provider="ollama", api_key="", model=""):
        self.provider = provider
        self.api_key = api_key
        self.model = model

    def effective_model(self):
        if self.model.strip():
            return self.model.strip()
        if self.provider == "gemini":
            return GEMINI_MODEL
        if self.provider == "groq":
            return GROQ_MODEL
        return MODEL_NAME

    def __repr__(self):
        return f"LLMConfig(provider={self.provider!r}, model={self.effective_model()!r})"


def _openai_compatible_base(provider):
    if provider == "gemini":
        return GEMINI_BASE_URL
    if provider == "groq":
        return GROQ_BASE_URL
    raise LLMError(f"Unknown online provider: {provider}")


def _call_http_provider(config, prompt, temperature, num_predict):
    """POST to an OpenAI-compatible endpoint (Gemini / Groq)."""

    if not config.api_key.strip():
        raise LLMError(
            f"Missing API key for {config.provider}. "
            "Paste your free key in the AI Engine section of the sidebar."
        )

    url = f"{_openai_compatible_base(config.provider)}/chat/completions"

    headers = {
        "Authorization": f"Bearer {config.api_key.strip()}",
        "Content-Type": "application/json",
    }

    body = {
        "model": config.effective_model(),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": num_predict,
    }

    try:
        response = httpx.post(
            url,
            headers=headers,
            json=body,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code

        if status == 401:
            raise LLMError(
                "API key rejected (401). Double-check the key in the sidebar."
            ) from exc
        if status == 404:
            raise LLMError(
                f"Model not found (404): {config.effective_model()!r}. "
                "Pick a model that exists on this provider."
            ) from exc
        if status == 429:
            raise LLMError(
                "Rate limit reached (429) on the free tier. "
                "Wait a minute and retry, or switch provider."
            ) from exc

        raise LLMError(f"Provider returned HTTP {status}.") from exc
    except httpx.ConnectError as exc:
        raise LLMError(
            "Could not reach the provider. Check your internet connection."
        ) from exc
    except httpx.TimeoutException as exc:
        raise LLMError(
            "The provider timed out. The request may have been large — retry."
        ) from exc

    try:
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError(
            f"Unexpected response shape from {config.provider}. "
            f"Raw: {response.text[:300]}"
        ) from exc


def _call_ollama(config, prompt, temperature, num_predict):
    """Local Ollama fallback (no internet required)."""

    try:
        from ollama import chat
        from ollama import ResponseError as OllamaResponseError
    except ImportError as exc:
        raise LLMError(
            "The 'ollama' Python package is not installed. "
            "Use an online provider instead."
        ) from exc

    try:
        response = chat(
            model=config.effective_model(),
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature, "num_predict": num_predict},
        )
    except OllamaResponseError as exc:
        status = getattr(exc, "status_code", None)

        if status == 404:
            raise LLMError(
                f"Local Ollama model {config.effective_model()!r} is not installed. "
                f"Pull it with: ollama pull {config.effective_model()}"
            ) from exc

        raise LLMError(f"Local Ollama returned an error (HTTP {status}).") from exc
    except ConnectionError as exc:
        raise LLMError(
            "Could not connect to the local Ollama server. "
            "Start it with `ollama serve` (and pull the model), or switch the "
            "AI Engine in the sidebar to an online provider."
        ) from exc

    return response["message"]["content"]


def chat(config, prompt, temperature=0.1, num_predict=4096):
    """
    Send a single-turn prompt to the configured provider.

    Returns the raw text response. Raises LLMError with a user-friendly
    message on any failure so the UI can show it directly.
    """

    if config.provider == "ollama":
        return _call_ollama(config, prompt, temperature, num_predict)

    return _call_http_provider(config, prompt, temperature, num_predict)


def test_connection(config):
    """
    Cheap probe call to verify a provider + key + model work.

    Returns (ok: bool, message: str) — never raises.
    """

    if config.provider == "ollama":
        return True, f"Local Ollama selected ({config.effective_model()})."

    if not config.api_key.strip():
        return False, "No API key provided."

    try:
        reply = chat(config, "Reply with the single word: OK", temperature=0.0, num_predict=8)
    except LLMError as exc:
        return False, str(exc)

    if "OK" in (reply or "").upper():
        return True, f"Connected to {config.provider} ({config.effective_model()})."

    return True, f"Connected to {config.provider} ({config.effective_model()}) — reply: {reply[:50]}"
