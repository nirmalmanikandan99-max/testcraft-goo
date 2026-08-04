# ✈️ TestCraft Goo — Complete Guide

AI-powered manual test case generator. Upload a functional document + user story, and it generates ready-to-use test cases (Conventional or Given/When/Then format) as a downloadable Excel file.

---

## 📍 How to Access

There are **three ways** to use TestCraft Goo, depending on where you are:

| Situation | URL / Method |
|---|---|
| 💻 On the office WiFi/network | `http://192.168.15.52:8501` |
| 🌍 Anywhere on the internet | `https://patterns-era-kinds-commerce.trycloudflare.com` *(changes if the tunnel restarts — ask the admin for the current link if it doesn't load)* |
| 🖥️ Fully offline, own machine | Double-click `TestCraftGoo.exe` in the `dist\TestCraftGoo\` folder (needs Ollama installed locally — see [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md)) |

All three run the exact same app — pick whichever is reachable for you.

---

## 🆕 First Time? Create an Account

1. Open the app link (above)
2. Click **🆕 Create Account**
3. Fill in: First Name, Last Name, Email, Phone Number, Password (min. 8 characters)
4. Click **✅ Create Account**
5. Switch to **🔐 Login**, sign in with your email/phone + password

You're in! Your account works across all three access methods (same login everywhere if using the same server; the desktop EXE keeps its own separate local account list).

---

## 🚀 How to Generate Test Cases

1. **Upload a Functional Document** (PDF, DOCX, or TXT) — sidebar, left side
2. *(Optional)* Upload Supporting Documents — extra context, any number of files
3. Choose **Test Case Format**: `Conventional Test Case` (7 columns) or `GWT` (Given/When/Then)
4. Fill in **User Story Title** and **Acceptance Criteria** (main area)
5. Click **🚀 Generate Test Cases**
6. Wait for the 4-stage pipeline: 🔍 Analyze requirements → 🎯 Select techniques → 🧪 Generate cases → 📊 Build Excel
7. Review results: metrics, test case table, requirement analysis, techniques used
8. Click **📥 Download Test Cases (Excel)**

---

## 🔧 For the Admin (Person Running the Server)

The web app runs from this machine. To start it after a restart:

```powershell
cd C:\AI-Test
venv\Scripts\python -m streamlit run app.py
```

To also make it reachable from the public internet, start the tunnel (separate terminal):

```powershell
cd C:\AI-Test
.\tools\cloudflared.exe tunnel --url http://localhost:8501
```

This prints a new `https://....trycloudflare.com` URL each time — share the new link with remote users.

**Requirements on this machine:**
- Python venv already set up (`venv\`)
- [Ollama](https://ollama.com) installed + `qwen2.5:7b` model pulled — see [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md)
- Windows Firewall rule allowing inbound port 8501 (already configured)

**User accounts** are stored in `users.db` (SQLite, password-hashed) — one shared database for the web app; the desktop EXE keeps its own copy inside its own folder.

---

## 📚 Related Guides

- [OLLAMA_SETUP_GUIDE.md](OLLAMA_SETUP_GUIDE.md) — installing Ollama + the AI model (needed for the desktop EXE, or to run the server itself)
- [DUCKDNS_SETUP_GUIDE.md](DUCKDNS_SETUP_GUIDE.md) — optional, only if a fixed (non-changing) public address is needed later

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| Public link doesn't load | Tunnel may have restarted with a new URL — ask the admin for the current link |
| "Invalid email/phone or password" | Double-check you signed up first; try the other identifier (email vs phone) |
| Office link (`192.168.15.52:8501`) doesn't load | You must be on the same office WiFi/network |
| Desktop EXE shows a blank/error page | Ensure Ollama is installed and running (`ollama serve`) with the `qwen2.5:7b` model pulled |
| "Requirement analysis returned invalid JSON" | Click Generate again — occasionally the AI model's first response needs a retry |
