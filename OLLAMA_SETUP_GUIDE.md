# TestCraft Goo — Ollama Setup & User Guide

TestCraft Goo uses a **local AI model** (via Ollama) to generate test cases —
no internet connection or API key is needed once set up. This guide walks
you through installing Ollama and using TestCraft Goo, whether you're
running it as a **desktop app (EXE)** or accessing it as a **web app** on
the office network.

---

## 1. What is Ollama?

Ollama runs AI language models directly on your own computer, for free,
with no subscription or API costs. TestCraft Goo uses the `qwen2.5:7b`
model through Ollama to analyze documents and generate test cases.

**System requirements:**
- Windows 10 / 11 (64-bit)
- At least 8 GB RAM (16 GB recommended)
- ~5 GB free disk space (for the model)
- No GPU required (works on CPU, though a GPU makes it faster)

---

## 2. Installing Ollama

1. Go to **https://ollama.com/download** and download the **Windows** installer.
2. Run the downloaded installer and follow the prompts (Next → Next → Install).
3. Once installed, Ollama runs automatically in the background (look for
   its icon in the system tray, near the clock).

To confirm it installed correctly, open **Command Prompt** or
**PowerShell** and run:

```
ollama --version
```

You should see a version number printed (e.g. `ollama version 0.4.7`).

---

## 3. Downloading the AI Model

TestCraft Goo needs the `qwen2.5:7b` model. Download it once with:

```
ollama pull qwen2.5:7b
```

This downloads about **4.7 GB** — it may take a few minutes depending on
your internet speed. You only need to do this **once per computer**.

To confirm the model is ready:

```
ollama list
```

You should see `qwen2.5:7b` in the list.

---

## 4. Running TestCraft Goo

### Option A — Desktop App (EXE)

1. Copy the entire **`TestCraftGoo`** folder to your computer (keep all
   files inside it together — the `.exe` needs its neighboring files).
2. Double-click **`TestCraftGoo.exe`**.
3. A browser tab opens automatically at `http://localhost:8501` — that's
   the app.
4. **First time?** Click **🆕 Create Account** and sign up with your name,
   email, phone number, and a password. Then switch to **🔐 Login**.
5. Keep the black console window open in the background while using the
   app — closing it will stop the app. Closing the browser tab alone is
   fine; just reopen `http://localhost:8501` to come back.

### Option B — Web App (Office Network)

If a colleague has already started TestCraft Goo as a shared web app on
the office network, you don't need to install anything except a browser:

1. Open your browser and go to the URL shared with you, e.g.:
   ```
   http://192.168.15.52:8501
   ```
2. Sign up (first time) or log in, and use the app as normal.

**Note:** In this setup, only the **host computer** (the one running the
app) needs Ollama and the model installed — everyone else just needs a
browser.

---

## 5. Using TestCraft Goo

1. **Upload Functional Document** — the main requirements document
   (PDF, DOCX, or TXT).
2. **Upload Supporting Documents** (optional) — any extra context files.
3. **Choose Test Case Format** — Conventional (7-column) or GWT
   (Given/When/Then).
4. **Enter User Story Title** and **Acceptance Criteria**.
5. Click **🚀 Generate Test Cases** and wait for the pipeline to finish
   (Analyze → Select Techniques → Generate → Build Excel).
6. Review the generated test cases, then click
   **📥 Download Test Cases (Excel)**.

---

## 6. Troubleshooting

| Problem | Solution |
|---|---|
| "Connection refused" / generation fails | Ollama isn't running. Check the system tray for the Ollama icon, or restart your computer. |
| Generation is very slow | Normal on CPU-only machines for the first request (model loads into memory). Later requests are faster. |
| `ollama: command not found` | Reinstall Ollama and restart your computer so it's added to PATH. |
| Model not found error | Run `ollama pull qwen2.5:7b` again — the download may not have completed. |
| App won't open / blank page | Make sure no other program is using port 8501. Close and reopen `TestCraftGoo.exe`. |
| Forgot password | There's currently no password reset — ask an admin to check the `users.db` file, or create a new account with a different email. |

---

## 7. Uninstalling

- **TestCraft Goo:** Just delete the `TestCraftGoo` folder.
- **Ollama:** Uninstall via Windows Settings → Apps, like any other program.
