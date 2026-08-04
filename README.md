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
- **Three AI engines** (choose in the sidebar):
  - 🌐 **Google Gemini 2.5 Flash** (free tier, ~1M tokens/day)
  - ⚡ **Groq** (free tier, ultra-fast Llama models)
  - 🖥️ **Local Ollama** (offline, fully private — `qwen2.5:7b`)
- **Bring Your Own Key (BYOK)** — each user saves their own free API key (encrypted on their account). No shared quota, no cost to you.
- **Two output formats** — Conventional (7-column) or GWT (Given/When/Then)
- **Multi-document input** — PDF, DOCX, TXT (primary + any number of supporting docs)
- **Persistent accounts** — stored on free **Neon Postgres** (SQLite fallback for local/offline use)
- **Polished UI** — gradient theme, live pipeline status, metrics, results tabs, styled Excel export
- **Desktop EXE** available for fully-offline use (needs local Ollama)

---

## 🆕 First Time? Create an Account

1. Open the app link above
2. Click **🆕 Create Account**
3. Fill in: First Name, Last Name, Email, Phone Number, Password (min. 8 chars)
4. *(Optional)* Expand **🌍 AI API Key** and paste your free Gemini/Groq key
5. Click **✅ Create Account**, then **🔐 Login**

> No key? You can add it later anytime from the sidebar → **🔑 My AI API Key**.

### Get a free API key

| Provider | Where to get it | Key looks like |
|---|---|---|
| Google Gemini | https://aistudio.google.com → "Get API key" | `AIza...` |
| Groq | https://console.groq.com → "API Keys" | `gsk_...` |

---

## 🚀 How to Generate Test Cases

1. **Upload a Functional Document** (PDF/DOCX/TXT) — sidebar, left side
2. *(Optional)* Add **Supporting Documents** — extra context
3. Choose **Test Case Format**: `Conventional Test Case` or `GWT`
4. Fill in **User Story Title** and **Acceptance Criteria** (main area)
5. Click **🚀 Generate Test Cases**
6. Watch the 4-stage pipeline run
7. Review: metrics, test-case table, requirement analysis, selected techniques
8. Click **📥 Download Test Cases (Excel)**

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

### Database: Neon (free Postgres)

1. Sign up at https://neon.tech → create a project
2. Copy the connection string (`postgresql://user:pass@ep-xxx...neon.tech/neondb?sslmode=require`)
3. Paste it into secrets as `DATABASE_URL` (both local `secrets.toml` and Cloud secrets)

The app auto-detects Postgres when `DATABASE_URL` is set, otherwise uses local SQLite.

---

## 📁 Project Structure

```
testcraft-goo/
├── app.py                     # Streamlit UI (login, sidebar, pipeline, results)
├── launcher.py                # Desktop EXE launcher (PyInstaller)
├── requirements.txt
├── .streamlit/config.toml     # Theme + toolbar config
├── src/
│   ├── auth.py                # Users, Neon/SQLite, encrypted API keys
│   ├── llm.py                 # Provider layer: Ollama / Gemini / Groq
│   ├── config.py              # Models, temperatures, endpoints
│   ├── document_loader.py     # PDF / DOCX / TXT extraction
│   ├── requirement_analyzer.py
│   ├── technique_selector.py
│   ├── testcase_generator.py
│   ├── json_validator.py      # Robust JSON extraction/parsing
│   └── excel_generator.py     # Styled Excel export
├── prompts/                   # LLM prompt templates per stage
└── tests/                     # Run as scripts (see below)
```

---

## 🧪 Running Tests

Tests are standalone scripts (no pytest needed):

```powershell
$env:PYTHONPATH="C:\AI-Test"
venv\Scripts\python tests\test_llm.py
venv\Scripts\python tests\test_auth.py
venv\Scripts\python tests\test_json_validator.py
venv\Scripts\python tests\test_excel_generator.py
```

`test_testcase_generator.py` requires a running local Ollama.

---

## 🔧 Desktop (Offline) Build

```powershell
venv\Scripts\python -m PyInstaller TestCraftGoo.spec
```

Double-click `dist\TestCraftGoo\TestCraftGoo.exe` → opens the app in your browser. Requires local Ollama with `qwen2.5:7b` — see [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md).

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| App shows "You don't have permission" | Repo must be **public** on GitHub; app must be set to **Public** in Cloud settings |
| "Missing API key" when generating online | Save your key in sidebar → **🔑 My AI API Key** |
| "Rate limit reached (429)" | Free-tier daily/minute quota hit — wait a minute and retry, or switch provider |
| "API key rejected (401)" | Check the key is correct for the selected provider (Gemini keys start `AIza`, Groq `gsk_`) |
| "Requirement analysis returned invalid JSON" | Click Generate again — occasionally the model's first response needs a retry |
| Local Ollama engine errors | Ensure Ollama is running (`ollama serve`) and `qwen2.5:7b` is pulled |
| Accounts resetting on Cloud | Add `DATABASE_URL` (Neon) secret — without it, Cloud storage is ephemeral |
| "Created by / Hosted with Streamlit" corner badge | Free-tier hosting branding, outside the app — auto-fades after ~5s; self-host to remove |

---

## 📚 Related Guides

- [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md) — local model setup (offline / EXE use)
- [DUCKDNS_SETUP_GUIDE.md](DUCKDNS_SETUP_GUIDE.md) — optional fixed public address for self-hosting
- [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md) — architecture, data flow, security
