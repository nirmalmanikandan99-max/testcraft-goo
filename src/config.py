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
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"

# Groq — OpenAI-compatible endpoint.
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Analysis and technique-selection are deterministic tasks -> low temperature.
ANALYSIS_TEMPERATURE = 0.1

# Test-case generation benefits from slightly more variety.
GENERATION_TEMPERATURE = 0.2

# Token budget per stage. Generation needs generous headroom so large
# JSON arrays are not truncated mid-array.
ANALYSIS_NUM_PREDICT = 300
GENERATION_NUM_PREDICT = 4096
