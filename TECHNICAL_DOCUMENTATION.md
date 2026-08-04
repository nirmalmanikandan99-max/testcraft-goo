# TestCraft Goo — Technical Documentation

This document describes the architecture, data flow, security model and deployment details of **TestCraft Goo**, an AI-powered manual test-case generator.

---

## 1. Overview

TestCraft Goo is a **single-module Streamlit application** that turns a functional document plus a user story into structured, downloadable test cases. It uses an LLM in a 4-stage pipeline and supports three AI backends, per-user API keys, and either local (SQLite) or cloud (Neon Postgres) user storage.

```
┌────────────┐   ┌─────────────┐   ┌──────────────┐   ┌─────────────┐
│ Requirement│   │  Technique  │   │  Test-Case   │   │   Excel     │
│  Analysis  │──▶│  Selection  │──▶│ Generation   │──▶│   Export    │
└────────────┘   └─────────────┘   └──────────────┘   └─────────────┘
      │                │                 │
      └────────────────┴─────────────────┘
                     │
              Unified LLM layer (src/llm.py)
              ┌──────────┬──────────┬──────────┐
              │  Ollama  │  Gemini  │   Groq   │
              └──────────┴──────────┴──────────┘
```

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Frontend / app framework | Streamlit 1.59 |
| AI inference (local) | Ollama (`qwen2.5:7b`) |
| AI inference (cloud) | Gemini 2.5 Flash / Groq Llama (OpenAI-compatible HTTP) |
| HTTP client | `httpx` |
| Auth storage | SQLite (local) **or** Neon Postgres (cloud) |
| Key encryption | Fernet (`cryptography`) |
| Document parsing | `pypdf`, `python-docx` |
| Excel export | `openpyxl` |
| Packaging | PyInstaller (`launcher.py` + `TestCraftGoo.spec`) |

---

## 3. Directory Layout

```
├── app.py                 # UI: auth gate, sidebar, 4-stage pipeline, results
├── launcher.py            # Desktop EXE bootstrap (starts Streamlit headless + opens browser)
├── requirements.txt
├── .streamlit/config.toml # Theme + client.toolbarMode="viewer"
├── prompts/               # Prompt templates (one per pipeline stage + formats)
│   ├── requirement_analysis_prompt.txt
│   ├── technique_selector_prompt.txt
│   ├── testcase_generator_prompt.txt
│   ├── conventional_prompt.txt
│   └── gwt_prompt.txt
├── src/
│   ├── __init__.py
│   ├── config.py          # Models, temperatures, token budgets, endpoints
│   ├── auth.py            # Users, DB abstraction, encrypted API keys
│   ├── llm.py             # Provider layer + connection test
│   ├── document_loader.py # read_pdf / read_docx / read_txt
│   ├── requirement_analyzer.py
│   ├── technique_selector.py
│   ├── testcase_generator.py
│   ├── json_validator.py  # Fence stripping + JSON extraction
│   └── excel_generator.py # Styled workbook, two layouts
└── tests/                 # Standalone scripts (run directly)
```

---

## 4. Pipeline Data Flow

1. **Input assembly** (`app.py`): document text + supporting docs + user story + format are combined into one `complete_context`.
2. **Stage 1 — `requirement_analyzer.analyze_requirements(context, llm_config)`**
   Calls the LLM with `requirement_analysis_prompt.txt`; expects JSON:
   ```json
   { "module_name": "", "summary": "", "input_fields": [], "business_rules": [],
     "validations": [], "workflow": [], "acceptance_criteria": [] }
   ```
3. **Stage 2 — `technique_selector.select_techniques(requirement_json, llm_config)`**
   Returns a JSON object of enabled testing techniques (`true/false`).
4. **Stage 3 — `testcase_generator.generate_testcases(requirement_json, technique_json, format, llm_config)`**
   Uses either `testcase_generator_prompt.txt` (7-column conventional) or `gwt_prompt.txt`. Expects an array of test-case objects.
5. **JSON safety — `json_validator.validate_json(raw)`**: strips ```json fences, tries `json.loads`, then falls back to extracting the outermost `[...]` or `{...}` block.
6. **Stage 4 — `excel_generator.generate_excel(test_cases, path, format)`**: writes a styled workbook (header fill, borders, freeze pane, auto-filter, column widths) with either the Conventional or GWT column layout.
7. Results are cached in `st.session_state["results"]` so they survive reruns (e.g. download clicks).

Every stage accepts an optional `llm_config` so the selected engine flows through the whole pipeline. On `LLMError`, the UI shows a friendly message and stops.

---

## 5. LLM Provider Layer (`src/llm.py`)

### `LLMConfig`
```python
LLMConfig(provider="ollama" | "gemini" | "groq", api_key="", model="")
# effective_model() resolves defaults per provider:
#   gemini -> "gemini-2.5-flash"    groq -> "llama-3.3-70b-versatile"
#   ollama -> MODEL_NAME ("qwen2.5:7b")
```

### `chat(config, prompt, temperature=0.1, num_predict=4096) -> str`
- **ollama**: lazy `from ollama import chat`; options `{temperature, num_predict}`.
- **gemini / groq**: POST to `{base}/chat/completions` (OpenAI-compatible) with
  `Authorization: Bearer <api_key>` and body `{model, messages, temperature, max_tokens}`.
  - Gemini base: `https://generativelanguage.googleapis.com/v1beta/openai`
  - Groq base: `https://api.groq.com/openai/v1`
- Raises `LLMError` with user-friendly messages for:
  - missing key, `401` (bad key), `404` (unknown model), `429` (rate limit),
    connection failure, timeout, unexpected response shape.

### `test_connection(config) -> (bool, str)`
Sends a tiny `"Reply with the single word: OK"` probe. Never raises.

> Keys are held only in memory (session state / DB decrypt-on-read) — never logged.

---

## 6. Authentication & Data Persistence (`src/auth.py`)

### Database abstraction
Selected at **module import time** from `DATABASE_URL`:
- Starts with `postgres` → `psycopg` (v3) with `dict_row` row factory.
- Otherwise → `sqlite3` with `Row` factory and `AUTH_DB_PATH` override (used by tests).

SQL placeholders are resolved per-dialect via `_placeholder()` (`?` vs `%s`).
`init_db()` runs DDL in **autocommit** mode — important on Postgres, where a failed
`ALTER TABLE` (e.g. column already exists) would otherwise abort the transaction and
roll back the `CREATE TABLE`.

### Schema (`users`)
| Column | Type | Notes |
|---|---|---|
| id | PK | `AUTOINCREMENT` (SQLite) / `SERIAL` (Postgres) |
| first_name / last_name / email / phone | TEXT | email & phone UNIQUE |
| password_hash / salt | TEXT | PBKDF2-HMAC-SHA256, 200k iterations |
| created_at | TEXT | ISO timestamp |
| api_provider | TEXT | `'gemini'` (default) / `'groq'` |
| api_model | TEXT | user-selected model |
| api_key_encrypted | TEXT | Fernet ciphertext ('' if none) |

### Security
- **Passwords**: salted PBKDF2-HMAC-SHA256 (`hashlib`), constant-time compare.
- **API keys**: encrypted with **Fernet**. The master key is resolved from
  `ENCRYPTION_KEY` (env / Streamlit secret); locally, a git-ignored `.encryption_key`
  file is auto-generated on first use.
- **Encryption round-trip** is covered by `tests/test_auth.py` (ciphertext never
  contains the plaintext key).

### Key management API
- `create_user(..., api_provider, api_model, api_key)` — optional key at signup
- `update_api_key(user_id, provider, model, api_key)` / `clear_api_key(user_id)`
- `get_api_key(user_id)` — decrypts on demand (returns `''` if none)
- `get_user_by_id(user_id)` — refreshed public profile after key edits
- `authenticate_user(identifier, password)` — login by email **or** phone

---

## 7. Configuration (`src/config.py`)

| Constant | Value | Purpose |
|---|---|---|
| `MODEL_NAME` | `qwen2.5:7b` | Local Ollama default |
| `GEMINI_MODEL` / `GEMINI_BASE_URL` | `gemini-2.5-flash` / `.../v1beta/openai` | Cloud provider |
| `GROQ_MODEL` / `GROQ_BASE_URL` | `llama-3.3-70b-versatile` / `api.groq.com/openai/v1` | Cloud provider |
| `ANALYSIS_TEMPERATURE` | `0.1` | Deterministic analysis/selection |
| `GENERATION_TEMPERATURE` | `0.2` | Slightly varied test cases |
| `ANALYSIS_NUM_PREDICT` | `300` | Token budget, stage 1–2 |
| `GENERATION_NUM_PREDICT` | `4096` | Headroom so large JSON arrays aren't truncated |

**Secrets** (`.streamlit/secrets.toml` locally / **Settings → Secrets** on Cloud):
```toml
DATABASE_URL = "postgresql://user:pass@ep-xxx...neon.tech/neondb?sslmode=require"
ENCRYPTION_KEY = "<fernet-key>"
```
`app.py` copies `st.secrets` values into `os.environ` before `init_db()` runs.

---

## 8. Deployment

### A. Local development
```powershell
python -m venv venv; venv\Scripts\activate
pip install -r requirements.txt
venv\Scripts\python -m streamlit run app.py
```
SQLite fallback is automatic when `DATABASE_URL` is absent. `.streamlit/secrets.toml`
and `.encryption_key` are git-ignored.

### B. Streamlit Community Cloud (free)
1. Public GitHub repo, branch `main`, main file `app.py`.
2. Secrets: `DATABASE_URL` + `ENCRYPTION_KEY`.
3. Auto-redeploys on every push.

### C. Desktop EXE (offline)
`launcher.py` switches to the frozen dir, opens the browser, and runs
`streamlit run app.py` headless. Requires local Ollama with the model pulled.

---

## 9. Testing

Run with the project root on `PYTHONPATH` (tests are scripts, not pytest):

| Script | Covers |
|---|---|
| `tests/test_llm.py` | Request shape/auth headers for Gemini & Groq (mocked `httpx`), default models, error mapping (401/404/429/connect), Ollama routing |
| `tests/test_auth.py` | Signup/login (email & phone), duplicate detection, key update/clear round-trip, encryption-at-rest (isolated temp SQLite DB) |
| `tests/test_json_validator.py` | JSON fence stripping / extraction |
| `tests/test_excel_generator.py` | Excel workbook generation |
| `tests/test_testcase_generator.py` | End-to-end stage 3 (requires running Ollama) |

---

## 10. Known Constraints & Free-Tier Limits

| Area | Limit |
|---|---|
| Gemini free tier | ~1M tokens/day, ~15 req/min per key |
| Groq free tier | ~100K tokens/day (Llama 70B), 6K tokens/min |
| Streamlit Cloud | Ephemeral disk (use Neon for persistence); hosting badge (outside app iframe, auto-fades ~5s) |
| Prompt/context | No chunking yet — very large PDFs can exceed context; consider RAG/chunking |
| Techniques | Hardcoded list in `technique_selector_prompt.txt` (~17 items) |
| Output | Single-sheet Excel; no editable pre-export review, no traceability matrix |

---

## 11. Roadmap (suggested)

1. Expanded technique catalog (30+) + pairwise/combinatorial generation
2. Multi-step test cases (steps, priority, severity) + selectable templates
3. Traceability matrix + requirement-coverage metrics
4. Editable review (`st.data_editor`) before export
5. Additional exports: CSV, JSON, Gherkin `.feature`, Xray/Zephyr formats
6. Document chunking / RAG for long inputs
7. Generation history (per-user, stored in Postgres)
8. Shared-key mode for admins (single key in secrets, no BYOK needed)
