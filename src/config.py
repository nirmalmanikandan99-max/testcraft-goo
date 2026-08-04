"""
Application Configuration

Single source of truth for model settings shared by every pipeline
stage (requirement analysis, technique selection, test-case generation).
"""

MODEL_NAME = "qwen2.5:7b"

# ------------------------------------------------------------------
# Online providers (free tiers, BYOK)
# ------------------------------------------------------------------

# Google AI Studio — OpenAI-compatible endpoint.
# gemini-2.5-flash was the old free default; 2026 projects ship 3.x models.
GEMINI_MODEL = "gemini-3-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

# On a 404, the provider layer retries these in order (first hit wins).
GEMINI_FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.1-flash-lite",
]

# Groq — OpenAI-compatible endpoint.
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-4-scout",
    "qwen3-32b",
]

# OpenRouter — aggregation gateway. Models ending in :free cost nothing
# (20 RPM; 50 req/day, or 1000/day after a one-time $10 credit top-up).
# Each :free model has its own daily bucket, so the fallback chain also
# multiplies the daily quota. Roster rotates frequently — verified live
# against openrouter.ai/api/v1/models (14 :free models currently).
#
# Ordering matters: GPT-OSS complied exactly (4-row arrays); the Nemotron
# reasoning models burn their output budget thinking and return 1 row.
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

OPENROUTER_FALLBACK_MODELS = [
    "openai/gpt-oss-20b:free",
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-26b-a4b-it:free",
]

# Analysis and technique-selection are deterministic tasks -> low temperature.
ANALYSIS_TEMPERATURE = 0.1

# Test-case generation benefits from slightly more variety.
GENERATION_TEMPERATURE = 0.2

# Token budget per stage. Gemini 3.x models "think" before answering and the
# thinking tokens count against max_tokens, so a budget that merely fits the
# JSON gets truncated mid-array on long-thinking calls. 16384 leaves headroom
# for both thinking and the full JSON (accepted by Gemini and Groq).
ANALYSIS_NUM_PREDICT = 16384
GENERATION_NUM_PREDICT = 16384

# System instruction prepended to every pipeline call: these tasks must
# produce parseable JSON, and frontier chat models often drift into
# markdown or prose without an explicit system role.
SYSTEM_JSON_RULE = (
    "You are an expert QA automation assistant. You always respond with ONE "
    "valid JSON object or array and nothing else. No markdown code fences, "
    "no explanations, no extra text outside the JSON."
)

# How many times a stage re-calls the model when its JSON fails to parse.
JSON_RETRIES = 3

# Stage 3 generates one focused call PER selected testing technique, then
# merges the results — this is what produces the technique combination.
# Cap the count to keep a run within free-tier per-minute request limits.
MAX_TECHNIQUES_PER_RUN = 8
MIN_CASES_PER_TECHNIQUE = 4
