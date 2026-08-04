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

import time

import httpx

from src.config import (
    GEMINI_BASE_URL,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MODEL,
    GROQ_BASE_URL,
    GROQ_FALLBACK_MODELS,
    GROQ_MODEL,
    MODEL_NAME,
    OPENROUTER_BASE_URL,
    OPENROUTER_FALLBACK_MODELS,
    OPENROUTER_MODEL,
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
        if self.provider == "openrouter":
            return OPENROUTER_MODEL
        return MODEL_NAME

    def __repr__(self):
        return f"LLMConfig(provider={self.provider!r}, model={self.effective_model()!r})"


def _openai_compatible_base(provider):
    if provider == "gemini":
        return GEMINI_BASE_URL
    if provider == "groq":
        return GROQ_BASE_URL
    if provider == "openrouter":
        return OPENROUTER_BASE_URL
    raise LLMError(f"Unknown online provider: {provider}")


def _model_candidates(config):
    """Configured model first, then known fallbacks for that provider."""

    if config.provider == "gemini":
        fallbacks = GEMINI_FALLBACK_MODELS
    elif config.provider == "groq":
        fallbacks = GROQ_FALLBACK_MODELS
    elif config.provider == "openrouter":
        fallbacks = OPENROUTER_FALLBACK_MODELS
    else:
        fallbacks = []

    # dict.fromkeys keeps order while de-duplicating.
    return list(dict.fromkeys([config.effective_model()] + fallbacks))


def _build_messages(prompt, system=None):
    if system:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
    return [{"role": "user", "content": prompt}]


def _post_with_429_backoff(url, headers, body, max_attempts=3):
    """POST, retrying on 429 (free-tier rate limit) with backoff.

    Free tiers (Gemini/Groq) throttle bursts; a short wait usually clears
    the per-minute window. Honors the Retry-After header when the provider
    sends one, otherwise waits 5s / 20s / 45s across the attempts.
    """

    fallback_waits = (5.0, 20.0, 45.0)

    for attempt in range(1, max_attempts + 1):
        response = httpx.post(url, headers=headers, json=body, timeout=DEFAULT_TIMEOUT)

        if response.status_code != 429 or attempt == max_attempts:
            return response

        wait = 0.0
        retry_after = response.headers.get("retry-after", "")
        try:
            wait = float(retry_after)
        except ValueError:
            wait = 0.0

        if wait <= 0:
            wait = fallback_waits[attempt - 1]

        wait = min(wait, 60.0)
        time.sleep(wait)

    return response


def _call_http_provider(config, prompt, temperature, num_predict, system=None, json_mode=False):
    """POST to an OpenAI-compatible endpoint (Gemini / Groq).

    - 404 (model renamed/removed): retries known fallback model IDs for the
      provider so stale model names keep working automatically.
    - 429 (free-tier rate limit): free-tier quotas are PER MODEL, so after
      backoff on one model the request moves to the next candidate, which
      has its own request budget. Only the first 429ed model gets the full
      backoff so worst-case wall time stays ~90s.
    """

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

    tried_models = []
    candidates = _model_candidates(config)
    saw_429 = False

    for model in candidates:
        tried_models.append(model)

        use_json_mode = json_mode

        while True:
            body = {
                "model": model,
                "messages": _build_messages(prompt, system),
                "temperature": temperature,
                "max_tokens": num_predict,
            }

            if use_json_mode:
                # Both providers require the word "json" somewhere in the
                # prompt when this mode is on; pipeline prompts mention it.
                body["response_format"] = {"type": "json_object"}

            try:
                # Full backoff only on the first model that rate-limits;
                # later candidates (separate quota buckets) get one shot.
                response = _post_with_429_backoff(
                    url, headers, body, max_attempts=3 if not saw_429 else 1
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code

                if status == 404:
                    break  # try the next known model ID

                if status == 429:
                    saw_429 = True
                    if model is not candidates[-1]:
                        # Each candidate has its own free-tier request budget.
                        time.sleep(3)
                    break  # next model; after the loop a 429 message is raised

                if status == 400 and use_json_mode:
                    # Some (OpenRouter :free) models reject response_format;
                    # retry the same model without it.
                    use_json_mode = False
                    continue

                if status == 402:
                    raise LLMError(
                        "OpenRouter: insufficient credits (402). Free-tier "
                        "models must end in ':free', or add credits to your "
                        "OpenRouter account."
                    ) from exc

                if status == 401:
                    raise LLMError(
                        "API key rejected (401). Double-check the key in the sidebar."
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

    if saw_429:
        raise LLMError(
            "Rate limit reached (429) on the free tier, even after automatic "
            "backoff retries across every candidate model. Per-minute limits "
            "reset within ~60s — wait a minute and retry. If 429s continue "
            "all day, the daily request limit (resets midnight Pacific) has "
            "been hit."
        )

    raise LLMError(
        f"Model not found (404): none of the tried models exist on {config.provider}. "
        f"Tried: {', '.join(tried_models)}. "
        "Check the model name in the AI Engine section of the sidebar."
    )


def list_models(config):
    """
    Fetch the provider's available model IDs (OpenAI-compatible GET /models).

    Returns a sorted list of IDs, or [] if unavailable / no key / offline.
    Used by the UI to show what actually works with a given key.
    """

    if config.provider == "ollama":
        return []

    if not config.api_key.strip():
        return []

    url = f"{_openai_compatible_base(config.provider)}/models"
    headers = {"Authorization": f"Bearer {config.api_key.strip()}"}

    try:
        response = httpx.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except Exception:
        return []

    try:
        models = response.json().get("data", [])
        ids = [m.get("id") for m in models if isinstance(m, dict) and m.get("id")]
        return sorted(set(ids))
    except Exception:
        return []


def _call_ollama(config, prompt, temperature, num_predict, system=None, json_mode=False):
    """Local Ollama fallback (no internet required)."""

    try:
        from ollama import chat
        from ollama import ResponseError as OllamaResponseError
    except ImportError as exc:
        raise LLMError(
            "The 'ollama' Python package is not installed. "
            "Use an online provider instead."
        ) from exc

    options = {"temperature": temperature, "num_predict": num_predict}
    if json_mode:
        options["format"] = "json"  # Ollama's structured output mode

    try:
        response = chat(
            model=config.effective_model(),
            messages=_build_messages(prompt, system),
            options=options,
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


def chat(config, prompt, temperature=0.1, num_predict=4096, system=None, json_mode=False):
    """
    Send a single-turn prompt to the configured provider.

    ``system`` (optional) is prepended as a system-role message, which is
    more reliable at enforcing output rules (e.g. strict JSON) than a note
    buried in the user prompt.

    ``json_mode=True`` asks the provider for guaranteed-JSON output
    (response_format on Gemini/Groq, format=json on Ollama).

    Returns the raw text response. Raises LLMError with a user-friendly
    message on any failure so the UI can show it directly.
    """

    if config.provider == "ollama":
        return _call_ollama(
            config, prompt, temperature, num_predict, system, json_mode
        )

    return _call_http_provider(
        config, prompt, temperature, num_predict, system, json_mode
    )


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
