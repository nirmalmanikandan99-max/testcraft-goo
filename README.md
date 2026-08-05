# ✈️ TestCraft Goo — Complete Guide

AI-powered **manual test case generator**. Upload a functional document + user story, and it generates ready-to-use test cases (Conventional or Given/When/Then format) as a downloadable Excel file — powered by free AI engines, with zero-cost hosting.

---

## 🚀 Live App

The app is deployed free on **Streamlit Community Cloud** and runs on any device with a browser:

> **https://testcraft-goo-mr8apnl3shbdhjbpaekwgz.streamlit.app**

No installs. No account needed to view — just sign up in-app (2 minutes) to start generating.

---

## ✨ Features

- **4-stage AI pipeline** — Requirement Analysis → Technique Selection → Test-Case Generation → Excel Export
- **Four AI engines** (choose in the sidebar):
  - 🖥️ **Local Ollama** (offline, fully private — `qwen2.5:7b`)
  - 🌐 **Google Gemini** (free tier — `gemini-3-flash`)
  - ⚡ **Groq** (free tier, ultra-fast Llama models)
  - 🔀 **OpenRouter** (free `:free` models — `google/gemma-4-26b-a4b-it:free` by default)
- **Technique combination** — test cases are generated per testing technique (up to 8 techniques per run, e.g. Positive, Negative, Boundary Value Analysis, Equivalence Partitioning, Decision Table...) and merged into one workbook with each case tagged by technique
- **Bring Your Own Key (BYOK)** — each user saves their own free API key (encrypted on their account). No shared quota, no cost to you
- **Generation Log download** — per-stage model used, token counts and rate-limit/quota status (including OpenRouter account usage)
- **Two output formats** — Conventional (7-column) or GWT (Given/When/Then)
- **Multi-document input** — PDF, DOCX, TXT (primary + any number of supporting docs)
- **Persistent accounts** — stored on free **Neon Postgres** (SQLite fallback for local/offline use)
- **Automatic resilience** — unknown model IDs fall back to alternates, 429 rate limits trigger backoff + model rotation, JSON output is validated and self-corrected, slow batches are skipped with a warning instead of hanging
- **Polished UI** — gradient theme, live pipeline status, metrics, results tabs, styled Excel export
- **Desktop EXE** available for fully-offline use (needs local Ollama)

---

## 🔑 AI Engine Setup (Step by Step)

The app supports **one local** and **three online** AI engines. Choose any engine in the sidebar, or at sign-up. Online engines need a **free API key** from their provider.

### Option 1 — Local Ollama (offline, no key, fully private)

1. Download & install Ollama from **https://ollama.com/download** (Windows installer, Next → Next → Install).
2. Verify it runs (system tray icon, or `ollama --version` in PowerShell).
3. Download the model once:
   ```powershell
   ollama pull qwen2.5:7b
   ```
   (≈4.7 GB download, one time only. Verify with `ollama list`.)
4. In the app, set **AI Engine → Local Ollama** (in the sidebar under *AI Engine*, or at sign-up). No key needed.
5. Generate as normal — everything runs on your machine.

> Full walkthrough (including the desktop EXE): [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md)

### Option 2 — Google Gemini (free tier)

1. Go to **https://aistudio.google.com** and sign in with your Google account.
2. Click **Get API key** (top right) → **Create API key** → choose your project.
3. Copy the key — it starts with `AIza...` (newer keys may start with `AQ.Ab8...`).
4. In the app: sidebar → **🔑 My AI API Key** → AI Engine: `🌍 Google Gemini (free tier)` → paste the key → **Save Key**.
   *(Or paste it in the **🌍 AI API Key** section when creating your account.)*
5. Leave the model as `gemini-3-flash` (or type a newer model ID, e.g. `gemini-3.5-flash` — unknown IDs are automatically retried against fallback models).

### Option 3 — Groq (free tier, fastest)

1. Create a free account at **https://console.groq.com** (sign in with Google/GitHub).
2. Go to **API Keys** → **Create API Key** → give it a name → copy the key (`gsk_...`).
3. In the app: sidebar → **🔑 My AI API Key** → AI Engine: `⚡ Groq (free tier)` → paste key → **Save Key**.
4. Default model: `llama-3.3-70b-versatile` (fallbacks: `llama-4-scout`, `qwen3-32b`).

### Option 4 — OpenRouter (free `:free` models)

1. Create a free account at **https://openrouter.ai**.
2. Go to **Keys** → **Create Key** → copy it (starts with `sk-or-v1-`).
3. In the app: sidebar → **🔑 My AI API Key** → AI Engine: `🔀 OpenRouter` → paste key → **Save Key**.
4. Default model: `google/gemma-4-26b-a4b-it:free` — chosen after live benchmarking for speed and output discipline. Any model ending in `:free` works.
5. *Quota note:* `:free` models allow ~20 requests/min and **50 requests/day** (raised to 1,000/day after a one-time $10 credit top-up). The app automatically rotates to the next free model when one is rate-limited.

### Provider comparison

| Engine | Key format | Get a key at | Cost | Limits (free) | Best for |
|---|---|---|---|---|---|
| Ollama (local) | none | — | Free | Your hardware (8 GB+ RAM) | Offline / privacy |
| Gemini | `AIza...` / `AQ.Ab8...` | aistudio.google.com | Free | ~10 req/min, ~1,500 req/day per model | Reliable quality |
| Groq | `gsk_...` | console.groq.com | Free | Very fast token rates | Speed |
| OpenRouter | `sk-or-v1-...` | openrouter.ai | Free (`:free`) | 20 req/min, 50 req/day (1,000/day after $10 top-up) | Many free models, auto-rotation |

---

## 🆕 First Time? Create an Account

1. Open the app link above
2. Click **🆕 Create Account**
3. Fill in: First Name, Last Name, Email, Phone Number, Password (min. 8 chars)
4. *(Optional)* Expand **🌍 AI API Key**, pick an engine and paste your free key (see setup steps above)
5. Click **✅ Create Account**, then **🔐 Login**

> No key yet? You can add one anytime from the sidebar → **🔑 My AI API Key**.

---

## 🚀 How to Generate Test Cases

1. **Upload a Functional Document** (PDF/DOCX/TXT) — sidebar, left side
2. *(Optional)* Add **Supporting Documents** — extra context
3. Choose **Test Case Format**: `Conventional Test Case` or `GWT`
4. Fill in **User Story Title**, **Acceptance Criteria**, and (optional) **Navigation** steps — one per line. Navigation becomes the *Actions to be done* (Conventional) / *When* (GWT) for every test case, ending with a final `Validate <Test Case Title>` step
5. Click **🚀 Generate Test Cases**
6. Watch the 4-stage pipeline run:
   - **Stage 1** — requirement analysis (structured JSON)
   - **Stage 2** — testing-technique selection
   - **Stage 3** — test-case generation, one *batch* per 2 techniques (each case tagged with its technique)
   - **Stage 4** — Excel export
7. Review: metrics, test-case table, requirement analysis, selected techniques
8. Click **📥 Download Test Cases (Excel)**
9. *(Optional)* Click **📄 Download Generation Log** — shows the model used per stage, tokens consumed, and your quota status (OpenRouter: free-tier usage & remaining daily requests)

> ⚠️ If a batch can't be generated (rate limit / provider congestion), it is **skipped with a warning** and the remaining cases are still exported.

---

## 🛠️ Run Locally (Development)

```powershell
# 1. Clone
git clone https://github.com/nirmalmanikandan99-max/testcraft-goo.git
cd testcraft-goo

# 2. Create venv & install
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# 3. (Optional) Enable Neon DB + encryption — create .streamlit/secrets.toml
DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"
ENCRYPTION_KEY = "<your-fernet-key>"

# 4. Run
venv\Scripts\python -m streamlit run app.py
```

Open http://localhost:8501.

- **No `secrets.toml`?** The app falls back to a local SQLite `users.db` and auto-generates an `.encryption_key` file — works fully offline with Ollama.
- **Generate an encryption key:**
  ```powershell
  venv\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

---

## ☁️ Deploy to Streamlit Community Cloud (free)

1. Push this repo to **GitHub** (public repo)
2. Go to https://share.streamlit.io → **New app** → pick the repo → branch `main` → main file `app.py` → **Deploy**
3. In the app → **Settings → Secrets**, add:
   ```toml
   DATABASE_URL = "postgresql://...neon.tech/neondb?sslmode=require"
   ENCRYPTION_KEY = "<your-fernet-key>"
   ```
4. Any future `git push` auto-redeploys the app

> **Important:** keep `ENCRYPTION_KEY` safe & unchanged — it's the only way to decrypt users' saved API keys.

> **Troubleshooting deploy:** after a push, the Cloud process sometimes re-runs the new code with a stale in-memory module (seen as `ImportError: cannot import name ...` on the app page). Open **Manage app → ⋮ → Reboot** to force a clean restart, or simply push again.

### Database: Neon (free Postgres)

1. Sign up at https://neon.tech → create a project
2. Copy the connection string (`postgresql://user:pass@ep-xxx...neon.tech/neondb?sslmode=require`)
3. Paste it into secrets as `DATABASE_URL` (both local `secrets.toml` and Cloud secrets)

The app auto-detects Postgres when `DATABASE_URL` is set, otherwise uses local SQLite.

---

## 📁 Project Structure

```
testcraft-goo/
├── app.py                     # Streamlit UI (login, sidebar, pipeline, results, generation log)
├── launcher.py                # Desktop EXE launcher (PyInstaller)
├── requirements.txt
├── .streamlit/config.toml     # Theme + toolbar config
├── prompts/                   # LLM prompt templates per stage
├── src/
│   ├── auth.py                # Users, Neon/SQLite, encrypted API keys
│   ├── llm.py                 # Provider layer: Ollama / Gemini / Groq / OpenRouter
│   │                           # (404 fallback chains, 429 backoff + rotation,
│   │                           #  JSON mode, usage log, quota lookups, time budget)
│   ├── config.py              # Models, temperatures, token budgets, endpoints
│   ├── document_loader.py     # PDF / DOCX / TXT extraction
│   ├── requirement_analyzer.py
│   ├── technique_selector.py
│   ├── testcase_generator.py  # Per-technique batched generation, skeleton + top-up,
│   │                           # grouping & merge
│   ├── json_validator.py      # Robust JSON extraction/parsing
│   └── excel_generator.py     # Styled Excel export
└── tests/                     # pytest suite (mock all LLM calls — no live API needed)
```

---

## 🧪 Running Tests

```powershell
$env:PYTHONPATH="C:\AI-Test"
venv\Scripts\python -m pytest tests -q
```

51 tests cover: provider request shapes & error mapping (401/404/429/402/timeout), model fallback chains, JSON mode, per-technique generation & merge, top-up retry, wall-clock budget, auth/encryption round-trip, JSON parsing, and Excel export. All LLM calls are mocked — no API key or Ollama needed.

> Note: `pytest` lives in the local venv only (not in `requirements.txt`, so the Cloud app stays lean).

---

## 🔧 Desktop (Offline) Build

**Already built:** the latest single-file EXE ships in the repo at
**`artifacts/TestCraftGoo.exe`** (~96 MB) — double-click it; a browser tab
opens with the app. Works offline with local Ollama, and also supports the
online engines when you have a key.

Rebuild it yourself (needs PyInstaller in the venv):

```powershell
venv\Scripts\python -m PyInstaller --clean --noconfirm TestCraftGoo_onefile.spec
Copy-Item dist\TestCraftGoo.exe artifacts\TestCraftGoo.exe -Force
```

The onedir variant (`TestCraftGoo.spec`, the old multi-file folder build)
is still supported — see [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md).

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| App shows "You don't have permission" | Repo must be **public** on GitHub; app must be set to **Public** in Cloud settings |
| "Missing API key" when generating online | Save your key in sidebar → **🔑 My AI API Key** |
| "Rate limit reached (429)" | Free-tier per-minute quota — wait ~60s and retry; the app already backoffs and rotates models automatically. All-day 429s = daily limit (resets midnight Pacific) |
| OpenRouter "insufficient credits (402)" | Free models must end in `:free`, or add credits to your OpenRouter account |
| "The provider timed out" / batch skipped | Free tier is congested — wait a minute and retry. The app gives a batch 180s, then skips it with a warning rather than hanging |
| "API key rejected (401)" | Check the key matches the selected provider (Gemini `AIza...`/`AQ.Ab8...`, Groq `gsk_`, OpenRouter `sk-or-v1-`) |
| Model not found (404) | The app auto-retries fallback models; check the model ID if it keeps failing |
| "Requirement analysis returned invalid JSON" | Click Generate again — the app feeds the bad output back to the model and retries up to 3 times |
| Local Ollama engine errors | Ensure Ollama is running (`ollama serve`) and `qwen2.5:7b` is pulled |
| ImportError right after a code push | Stale in-memory module on Cloud — **Manage app → ⋮ → Reboot** (or push again) |
| Accounts resetting on Cloud | Add `DATABASE_URL` (Neon) secret — without it, Cloud storage is ephemeral |
| "Created by / Hosted with Streamlit" corner badge | Free-tier hosting branding, outside the app — auto-fades after ~5s; self-host to remove |

---

## 📚 Related Guides

- [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md) — local model setup (offline / EXE use)
- [DUCKDNS_SETUP_GUIDE.md](DUCKDNS_SETUP_GUIDE.md) — optional fixed public address for self-hosting
- [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md) — architecture, data flow, security
