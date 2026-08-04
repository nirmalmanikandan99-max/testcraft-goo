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

# Analysis and technique-selection are deterministic tasks -> low temperature.
ANALYSIS_TEMPERATURE = 0.1

# Test-case generation benefits from slightly more variety.
GENERATION_TEMPERATURE = 0.2

# Token budget per stage. Generation needs generous headroom so large
# JSON arrays are not truncated mid-array.
ANALYSIS_NUM_PREDICT = 1024
GENERATION_NUM_PREDICT = 4096

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
