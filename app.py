import os
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

from src.document_loader import (
    read_pdf,
    read_docx,
    read_txt
)
from src.requirement_analyzer import analyze_requirements
from src.technique_selector import select_techniques
from src.testcase_generator import (
    generate_testcases,
    generate_testcases_for_techniques,
    group_rows_by_technique,
    merge_technique_testcases,
)
from src.json_validator import validate_json
from src.excel_generator import generate_excel
from src.auth import (
    init_db,
    create_user,
    authenticate_user,
    validate_signup_fields,
    get_user_by_id,
    get_api_key,
    update_api_key,
    clear_api_key,
)
from src import llm as llm_mod
from src.llm import LLMConfig, LLMError, test_connection, list_models
from src.config import (
    JSON_RETRIES,
    GEMINI_MODEL,
    GROQ_MODEL,
    MAX_TECHNIQUES_PER_RUN,
    OPENROUTER_MODEL,
    TECHNIQUES_PER_BATCH,
)

PROVIDER_OPTIONS = ["gemini", "groq", "openrouter"]

PROVIDER_LABELS = {
    "gemini": "🌍 Google Gemini (free tier)",
    "groq": "⚡ Groq (free tier)",
    "openrouter": "🔀 OpenRouter (free :free models)",
}

PROVIDER_DEFAULT_MODELS = {
    "gemini": GEMINI_MODEL,
    "groq": GROQ_MODEL,
    "openrouter": OPENROUTER_MODEL,
}

# ------------------------------------------------------------------
# Cloud secrets -> environment (Neon DB + encryption master key).
# Local development keeps SQLite + a generated .encryption_key file.
# ------------------------------------------------------------------

if not os.environ.get("DATABASE_URL") and "DATABASE_URL" in st.secrets:
    os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]

if not os.environ.get("ENCRYPTION_KEY") and "ENCRYPTION_KEY" in st.secrets:
    os.environ["ENCRYPTION_KEY"] = st.secrets["ENCRYPTION_KEY"]

# ==========================================================
# Page Configuration
# ==========================================================

st.set_page_config(
    page_title="TestCraft Goo",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# Styling (Modern, vibrant theme — indigo → violet → pink)
# ==========================================================

st.markdown(
    """
    <style>
      /* Hide Streamlit chrome: menu, footer, "Created by", Deploy bar */
      #MainMenu { display: none !important; }
      footer { display: none !important; }
      [data-testid="stFooter"] { display: none !important; }
      [data-testid="stToolbar"] { display: none !important; }
      [data-testid="stDecoration"] { display: none !important; }
      [data-testid="stStatusWidget"] { display: none !important; }
      [data-testid="stAppDeployButton"] { display: none !important; }
      header[data-testid="stHeader"] { display: none !important; }

      /* Layout */
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }

      /* ---------- Hero header ---------- */
      .hero {
          display: flex; align-items: center; gap: 1.2rem;
          background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 48%, #EC4899 100%);
          padding: 1.7rem 2rem;
          border-radius: 20px;
          color: #ffffff;
          margin-bottom: 1.6rem;
          box-shadow: 0 12px 30px rgba(124, 58, 237, 0.32);
      }
      .hero-badge {
          flex: 0 0 auto;
          width: 66px; height: 66px;
          border-radius: 18px;
          background: rgba(255, 255, 255, 0.18);
          border: 1px solid rgba(255, 255, 255, 0.35);
          display: flex; align-items: center; justify-content: center;
          font-size: 2.2rem; line-height: 1;
          box-shadow: inset 0 1px 6px rgba(255, 255, 255, 0.25);
      }
      .hero h1 { color: #ffffff; margin: 0; font-size: 2rem; font-weight: 800; letter-spacing: -0.6px; }
      .hero p  { color: #f0e9ff; margin: 0.4rem 0 0; font-size: 1.02rem; }

      /* ---------- Section titles ---------- */
      .section-title {
          font-size: 1.14rem; font-weight: 700; color: #6D28D9;
          margin: 0.2rem 0 0.7rem; display: flex; align-items: center; gap: 0.55rem;
      }
      .section-title .ico { font-size: 1.25rem; line-height: 1; }

      /* ---------- Sidebar ---------- */
      section[data-testid="stSidebar"] { background: #F5F4FF; border-right: 1px solid #E5E1FB; }
      section[data-testid="stSidebar"] h2,
      section[data-testid="stSidebar"] h3 { color: #6D28D9; }
      .side-brand { display: flex; align-items: center; gap: 0.55rem; font-size: 1.25rem; font-weight: 800; color: #6D28D9; }
      .side-brand .ico { font-size: 1.5rem; line-height: 1; }

      /* ---------- Primary buttons (gradient) ---------- */
      .stButton > button {
          background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
          color: #ffffff; border: none; border-radius: 12px;
          padding: 0.75rem 1rem; font-weight: 700; font-size: 1.05rem;
          transition: all 0.18s ease; box-shadow: 0 6px 16px rgba(99, 102, 241, 0.30);
      }
      .stButton > button:hover {
          background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
          box-shadow: 0 10px 22px rgba(99, 102, 241, 0.42);
          transform: translateY(-2px); color: #ffffff;
      }

      /* ---------- Download button (emerald) ---------- */
      .stDownloadButton > button {
          background: linear-gradient(135deg, #10B981 0%, #059669 100%);
          color: #ffffff; border: none; border-radius: 12px;
          font-weight: 700; padding: 0.75rem 1rem;
          box-shadow: 0 6px 16px rgba(16, 185, 129, 0.30);
      }
      .stDownloadButton > button:hover {
          background: linear-gradient(135deg, #059669 0%, #047857 100%);
          box-shadow: 0 10px 22px rgba(16, 185, 129, 0.42);
          transform: translateY(-2px); color: #ffffff;
      }

      /* ---------- Metric cards ---------- */
      div[data-testid="stMetric"] {
          background: #ffffff; border: 1px solid #E5E1FB; border-left: 4px solid #8B5CF6;
          border-radius: 14px; padding: 0.9rem 1.1rem;
          box-shadow: 0 4px 12px rgba(124, 58, 237, 0.06);
      }
      div[data-testid="stMetricLabel"] p { color: #7C3AED; font-weight: 700; }

      /* ---------- Tabs ---------- */
      .stTabs [data-baseweb="tab-list"] { gap: 0.35rem; }
      .stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: 0.45rem 1.05rem; font-weight: 700; }
      .stTabs [aria-selected="true"] { color: #6D28D9; }

      hr { margin: 1.1rem 0; border-color: #ECE9FB; }

      /* ---------- Footer ---------- */
      .footer-container {
          margin-top: 2.5rem;
          padding-top: 1.8rem;
          border-top: 1px solid #ECE9FB;
          text-align: center;
      }
      .footer-stats {
          display: flex; justify-content: center; align-items: center; gap: 1.6rem;
          flex-wrap: wrap;
          margin-bottom: 0.8rem;
      }
      .stat-badge {
          background: linear-gradient(135deg, #F5F4FF 0%, #ECE9FB 100%);
          border: 1px solid #D8D0F5;
          border-radius: 12px;
          padding: 0.65rem 1.1rem;
          font-weight: 700;
          color: #6D28D9;
          font-size: 0.95rem;
          box-shadow: 0 2px 8px rgba(124, 58, 237, 0.08);
      }
      .footer-quote {
          color: #8B5CF6;
          font-size: 0.9rem;
          font-style: italic;
          margin-top: 0.5rem;
      }
    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================================
# Helpers
# ==========================================================

def read_uploaded_file(uploaded_file):
    """Read a single uploaded file by extension."""
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return read_pdf(uploaded_file)
    if name.endswith(".docx"):
        return read_docx(uploaded_file)
    if name.endswith(".txt"):
        return read_txt(uploaded_file)

    return ""


def count_applicable_techniques(technique_json):
    """Number of techniques marked True in the selection object."""
    if isinstance(technique_json, dict):
        return sum(1 for v in technique_json.values() if v is True)
    return 0


def section_title(icon, text):
    """Render a consistent section heading with a well-sized icon."""
    st.markdown(
        f'<div class="section-title"><span class="ico">{icon}</span>{text}</div>',
        unsafe_allow_html=True
    )


def render_auth_page():
    """Render the Login / Create Account gate."""

    st.markdown(
        """
        <div class="hero">
            <div class="hero-badge">✈️</div>
            <div>
                <h1>TestCraft Goo</h1>
                <p>Generate manual test cases from functional documents and user stories — powered by a local LLM.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    _left, center, _right = st.columns([1, 1.4, 1])

    with center:

        mode = st.radio(
            "Choose action",
            options=["🔐 Login", "🆕 Create Account"],
            horizontal=True,
            label_visibility="collapsed"
        )

        st.markdown("")

        if mode == "🔐 Login":

            with st.container(border=True):
                section_title("🔐", "Login")

                identifier = st.text_input(
                    "Email or Phone Number",
                    placeholder="you@example.com or +91XXXXXXXXXX"
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password"
                )

                if st.button("➡️ Login", use_container_width=True):

                    if not identifier.strip() or not password:
                        st.error("⚠️ Please enter both identifier and password.")
                    else:
                        user = authenticate_user(identifier, password)

                        if user is None:
                            st.error("❌ Invalid email/phone or password.")
                        else:
                            st.session_state["auth_user"] = user
                            st.rerun()

        else:

            with st.container(border=True):
                section_title("🆕", "Create Account")

                c1, c2 = st.columns(2)
                first_name = c1.text_input("First Name", placeholder="John")
                last_name = c2.text_input("Last Name", placeholder="Doe")

                email = st.text_input("Email", placeholder="you@example.com")
                phone = st.text_input("Phone Number", placeholder="+91XXXXXXXXXX")

                p1, p2 = st.columns(2)
                password = p1.text_input(
                    "Password", type="password", placeholder="At least 8 characters"
                )
                confirm_password = p2.text_input(
                    "Confirm Password", type="password", placeholder="Re-enter password"
                )

                with st.expander("🌍 AI API Key (optional)"):
                    st.caption(
                        "Skip this for now and add it later from the sidebar. "
                        "Free keys: Gemini → aistudio.google.com · "
                        "Groq → console.groq.com · OpenRouter → openrouter.ai/keys"
                    )
                    api_provider = st.selectbox(
                        "Provider",
                        options=PROVIDER_OPTIONS,
                        format_func=lambda p: PROVIDER_LABELS[p],
                        key="signup_api_provider",
                    )
                    api_model = st.text_input(
                        "Model",
                        value=PROVIDER_DEFAULT_MODELS[api_provider],
                        key="signup_api_model",
                    )
                    api_key_input = st.text_input(
                        "API Key",
                        type="password",
                        placeholder="Paste your free API key here",
                        key="signup_api_key",
                    )

                if st.button("✅ Create Account", use_container_width=True):

                    error = validate_signup_fields(
                        first_name, last_name, email, phone, password, confirm_password
                    )

                    if error:
                        st.error(f"⚠️ {error}")
                    else:
                        success, message = create_user(
                            first_name,
                            last_name,
                            email,
                            phone,
                            password,
                            api_provider=api_provider,
                            api_model=api_model.strip(),
                            api_key=api_key_input,
                        )

                        if success:
                            st.success(f"✅ {message} Please switch to Login above.")
                        else:
                            st.error(f"❌ {message}")

    st.markdown(
        """
        <div class="footer-container">
            <div class="footer-stats">
                <div class="stat-badge">⚡ Speed 1Tera Hetz</div>
                <div class="stat-badge">💾 Memory 1Zita Byte</div>
            </div>
            <div class="footer-quote">✈️ TestCraft Goo — Powered by Innovation</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# Authentication Gate
# ==========================================================

init_db()

if "auth_user" not in st.session_state:
    render_auth_page()
    st.stop()


# ==========================================================
# Sidebar — Inputs & Configuration
# ==========================================================

document_text = ""
supporting_document_text = ""

with st.sidebar:

    st.markdown(
        '<div class="side-brand"><span class="ico">✈️</span>TestCraft Goo</div>',
        unsafe_allow_html=True
    )
    st.caption("AI-powered manual test case generation")

    st.markdown("---")

    # ----- Logged-in user -----
    current_user = st.session_state["auth_user"]
    st.markdown(f"👋 **Welcome, {current_user['first_name']}!**")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.pop("auth_user", None)
        st.session_state.pop("results", None)
        st.rerun()

    st.markdown("---")

    # ----- Functional Document -----
    section_title("📁", "Functional Document")

    fd = st.file_uploader(
        "Upload the primary functional document",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed"
    )

    if fd is not None:
        with st.spinner("Reading document..."):
            document_text = read_uploaded_file(fd)
        st.success(f"✅ {fd.name}")

    # ----- Supporting Documents -----
    section_title("📎", "Supporting Documents")

    support_docs = st.file_uploader(
        "Optional supporting documents",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if support_docs:
        with st.spinner("Reading supporting documents..."):
            for file in support_docs:
                supporting_document_text += read_uploaded_file(file) + "\n\n"
        st.success(f"✅ {len(support_docs)} file(s) loaded")

    st.markdown("---")

    # ----- Test Case Format -----
    section_title("🎛️", "Test Case Format")

    test_case_format = st.radio(
        "Choose the required format",
        options=["Conventional Test Case", "GWT"],
        label_visibility="collapsed"
    )

    st.caption(
        "Conventional → 7-column format\n\nGWT → Given / When / Then"
    )

    st.markdown("---")

    # ----- AI Engine -----
    section_title("⚙️", "AI Engine")

    # On the cloud host there is no local Ollama, so default to Online.
    is_cloud = bool(os.environ.get("DATABASE_URL"))

    engine_choice = st.radio(
        "Engine",
        options=["🖥️ Local (Ollama)", "🌐 Online (Saved API Key)"],
        label_visibility="collapsed",
        index=1 if is_cloud else 0,
    )

    provider = "ollama"
    model = ""
    api_key = ""

    if engine_choice.startswith("🌐"):
        provider = current_user.get("api_provider") or "gemini"
        model = current_user.get("api_model") or ""
        api_key = get_api_key(current_user["id"])

        if not current_user.get("has_api_key"):
            st.warning(
                "⚠️ No API key on your account yet — save one below "
                "to use free online generation."
            )
    elif is_cloud:
        st.warning(
            "⚠️ Local Ollama is not available on the cloud host. "
            "Switch to Online, or run the app on your own machine."
        )

    llm_config = LLMConfig(
        provider=provider,
        api_key=api_key,
        model=model,
    )

    engine_label = (
        f"your {provider} model ({llm_config.effective_model()})"
        if provider != "ollama"
        else "a local Ollama model (offline)"
    )

    st.markdown("---")

    # ----- Per-user API key management -----
    section_title("🔑", "My AI API Key")

    with st.expander(
        "Manage my key",
        expanded=not current_user.get("has_api_key"),
    ):
        key_provider = st.selectbox(
            "Provider",
            options=PROVIDER_OPTIONS,
            format_func=lambda p: PROVIDER_LABELS[p],
            key="key_provider",
            index=PROVIDER_OPTIONS.index(
                (current_user.get("api_provider") or "gemini")
                if (current_user.get("api_provider") or "gemini") in PROVIDER_OPTIONS
                else "gemini"
            ),
        )

        key_default_model = PROVIDER_DEFAULT_MODELS[key_provider]

        key_model = st.text_input(
            "Model",
            value=current_user.get("api_model") or key_default_model,
            key="key_model",
        )

        key_input = st.text_input(
            "API Key",
            type="password",
            placeholder="Paste your free key here — encrypted on your account",
            key="key_input",
        )

        col_save, col_remove = st.columns(2)

        if col_save.button("💾 Save Key", use_container_width=True):
            if not key_input.strip():
                st.error("⚠️ Please paste an API key first.")
            else:
                update_api_key(
                    current_user["id"],
                    key_provider,
                    key_model.strip() or key_default_model,
                    key_input.strip(),
                )
                st.session_state["auth_user"] = get_user_by_id(current_user["id"])
                st.success("✅ Key saved to your account.")
                st.rerun()

        if current_user.get("has_api_key"):
            if col_remove.button("🗑️ Remove", use_container_width=True):
                clear_api_key(current_user["id"])
                st.session_state["auth_user"] = get_user_by_id(current_user["id"])
                st.rerun()

        if current_user.get("has_api_key"):
            st.caption(
                f"Current: {current_user['api_provider']} · "
                f"{current_user.get('api_model') or 'default model'}"
            )

            if st.button("🔌 Test Connection", use_container_width=True):
                with st.spinner("Testing connection..."):
                    ok, message = test_connection(
                        LLMConfig(
                            provider=current_user["api_provider"],
                            api_key=get_api_key(current_user["id"]),
                            model=current_user.get("api_model") or "",
                        )
                    )
                if ok:
                    st.success(f"✅ {message}")

                    available = list_models(
                        LLMConfig(
                            provider=current_user["api_provider"],
                            api_key=get_api_key(current_user["id"]),
                        )
                    )

                    if available:
                        st.caption(
                            "Available models: "
                            + ", ".join(available[:8])
                            + (" …" if len(available) > 8 else "")
                        )
                else:
                    st.error(f"❌ {message}")


# ==========================================================
# Main — Hero Header
# ==========================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-badge">✈️</div>
        <div>
            <h1>TestCraft Goo</h1>
            <p>Generate manual test cases from functional documents and user stories — powered by {engine_label}.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ----- Document preview (main area, only if uploaded) -----
if document_text:
    with st.expander("📄 View extracted document content"):
        st.text_area("Functional document", value=document_text, height=240, label_visibility="collapsed")

if supporting_document_text:
    with st.expander("📄 View supporting documents content"):
        st.text_area("Supporting documents", value=supporting_document_text, height=240, label_visibility="collapsed")


# ==========================================================
# Main — User Story
# ==========================================================

section_title("✍️", "User Story Details")

with st.container(border=True):
    story_title = st.text_input("User Story Title", placeholder="e.g. As a user, I want to log in securely")

    acceptance = st.text_area(
        "Acceptance Criteria",
        height=200,
        placeholder="List the acceptance criteria, one per line..."
    )

st.markdown("")

generate_clicked = st.button("🚀 Generate Test Cases", use_container_width=True)


# ==========================================================
# Generation Pipeline
# ==========================================================

def _stage_with_retry(run_stage, status, stage_label):
    """
    Run one pipeline stage (a callable taking an optional retry_hint).

    Models occasionally answer with prose/markdown instead of JSON. When the
    parse fails, re-call with the failed output fed back as a correction
    hint, up to JSON_RETRIES attempts. Returns (parsed_json, raw_text);
    parsed_json is None if every attempt failed.
    """

    raw = ""
    for attempt in range(1, JSON_RETRIES + 1):
        if attempt > 1:
            st.write(
                f"⚠️ {stage_label} response was not valid JSON — "
                f"correcting and retrying ({attempt}/{JSON_RETRIES})..."
            )

        retry_hint = None
        if attempt > 1:
            retry_hint = (
                "Your previous response could not be parsed as JSON — the "
                "application rejected it. Return ONLY a single valid JSON "
                "object or array this time: no markdown code fences, no "
                "explanations, nothing before or after the JSON.\n"
                f"Preview of your invalid response: {raw[:300]}"
            )

        raw = run_stage(retry_hint)
        parsed = validate_json(raw)
        if parsed is not None:
            return parsed, raw

    return None, raw


def _build_generation_log(usage_sections, story_title, test_case_format, account_limits=None):
    """
    Render the downloadable generation log: per stage — model used, tokens
    consumed, and the rate-limit/remaining-quota headers the provider
    returned. usage_sections is a list of (stage_label, [usage events]).
    """

    lines = []
    lines.append("=" * 64)
    lines.append(" TestCraft Goo - Generation Log")
    lines.append("=" * 64)
    lines.append(f"Generated at      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"User Story        : {story_title}")
    lines.append(f"Test Case Format  : {test_case_format}")

    total_in = sum(e["prompt_tokens"] for _, evs in usage_sections for e in evs)
    total_out = sum(e["completion_tokens"] for _, evs in usage_sections for e in evs)
    total_calls = sum(len(evs) for _, evs in usage_sections)

    lines.append(f"Total API calls   : {total_calls}")
    lines.append(
        f"Total tokens used : {total_in + total_out} "
        f"(input {total_in} + output {total_out})"
    )
    lines.append("")

    for stage_label, events in usage_sections:
        lines.append("-" * 64)
        lines.append(f"  {stage_label}")
        lines.append("-" * 64)

        if not events:
            lines.append("  (no successful API call recorded for this stage)")
            lines.append("")
            continue

        for event in events:
            lines.append(f"  Model      : {event['provider']} / {event['model']}")
            lines.append(
                f"  Tokens     : input {event['prompt_tokens']} | "
                f"output {event['completion_tokens']} | "
                f"total {event['total_tokens']}"
            )
            limits = event.get("rate_limits") or {}
            if limits:
                lines.append("  Limit / quota remaining (from provider response):")
                for key, value in limits.items():
                    lines.append(f"    {key}: {value}")
            else:
                lines.append(
                    "  Limit / quota remaining: not reported on this call"
                )
            lines.append("")

    if account_limits:
        lines.append("=" * 64)
        lines.append("  Provider account status")
        lines.append("=" * 64)
        lines.append(
            f"  Free tier         : "
            f"{'yes' if account_limits.get('free_tier') else 'no'}"
        )
        lines.append(
            f"  Credits used      : "
            f"${float(account_limits.get('usage_usd') or 0):.6f}"
        )
        lines.append(
            f"  Usage (daily)     : "
            f"${float(account_limits.get('usage_daily_usd') or 0):.6f}"
        )
        lines.append(
            "  Free-model budget : 50 requests/day (20/min); rises to "
            "1,000/day after a one-time $10 credit top-up."
        )
        lines.append(
            "  Note              : OpenRouter free models are request-based, "
            "not token-based; token availability applies to Gemini/Groq."
        )
        lines.append("")

    lines.append("=" * 64)
    lines.append(
        "Note: 'remaining' values come from the provider's own rate-limit "
        "response headers; they are per-model free-tier budgets and reset "
        "per minute / per day."
    )
    return "\n".join(lines)


if generate_clicked:

    if fd is None:
        st.error("⚠️ Please upload the Functional Document from the sidebar.")

    elif story_title.strip() == "":
        st.error("⚠️ Please enter the User Story Title.")

    elif acceptance.strip() == "":
        st.error("⚠️ Please enter the Acceptance Criteria.")

    else:

        complete_context = f"""
===========================
FUNCTIONAL DOCUMENT
===========================

{document_text}

===========================
SUPPORTING DOCUMENTS
===========================

{supporting_document_text}

===========================
USER STORY
===========================

Title:
{story_title}

Acceptance Criteria:
{acceptance}

===========================
TEST CASE FORMAT
===========================

{test_case_format}
"""

        # Clear any previous run
        st.session_state.pop("results", None)
        llm_mod.clear_usage_log()

        # Usage events per pipeline stage, for the downloadable log.
        usage_sections = []

        with st.status("Running generation pipeline...", expanded=True) as status:

            # ---- Stage 1: Requirement Analysis ----
            st.write("🔍 **Stage 1** — Analyzing requirements...")
            usage_mark = len(llm_mod.usage_log())
            try:
                requirement_json, requirement_raw = _stage_with_retry(
                    lambda hint: analyze_requirements(
                        complete_context, llm_config, retry_hint=hint
                    ),
                    status,
                    "Requirement analysis",
                )
            except LLMError as exc:
                status.update(label="❌ Requirement analysis failed", state="error")
                st.error(f"❌ {exc}")
                st.stop()
            usage_sections.append(
                ("Stage 1 - Requirement Analysis", llm_mod.usage_log()[usage_mark:])
            )

            if requirement_json is None:
                status.update(label="❌ Requirement analysis failed", state="error")
                st.error(
                    f"Requirement analysis returned invalid JSON after "
                    f"{JSON_RETRIES} attempts. Please try again."
                )
                with st.expander("View raw model output"):
                    st.code(requirement_raw)
                st.stop()

            # Free-tier quotas (Gemini/Groq) are ~10-15 requests/minute;
            # spacing stage calls keeps a run under the ceiling even with
            # retries.
            st.write("⏳ Brief pause to stay within free-tier rate limits...")
            time.sleep(5)

            # ---- Stage 2: Technique Selection ----
            st.write("🎯 **Stage 2** — Selecting testing techniques...")
            usage_mark = len(llm_mod.usage_log())
            try:
                technique_json, technique_raw = _stage_with_retry(
                    lambda hint: select_techniques(
                        requirement_json, llm_config, retry_hint=hint
                    ),
                    status,
                    "Technique selection",
                )
            except LLMError as exc:
                status.update(label="❌ Technique selection failed", state="error")
                st.error(f"❌ {exc}")
                st.stop()
            usage_sections.append(
                ("Stage 2 - Technique Selection", llm_mod.usage_log()[usage_mark:])
            )

            if technique_json is None:
                status.update(label="❌ Technique selection failed", state="error")
                st.error(
                    f"Technique selection returned invalid JSON after "
                    f"{JSON_RETRIES} attempts. Please try again."
                )
                with st.expander("View raw model output"):
                    st.code(technique_raw)
                st.stop()

            st.write("⏳ Brief pause to stay within free-tier rate limits...")
            time.sleep(5)

            # ---- Stage 3: Test Case Generation (per technique) ----
            st.write("🧪 **Stage 3** — Generating test cases per technique...")

            selected_techniques = [
                technique
                for technique, enabled in (technique_json or {}).items()
                if enabled is True or str(enabled).lower() in ("true", "yes", "1")
            ][:MAX_TECHNIQUES_PER_RUN]

            usage_mark = len(llm_mod.usage_log())

            if selected_techniques:
                # Batch several techniques per generation call — many small
                # calls on free-tier providers run past 3 minutes and time out.
                batches = [
                    selected_techniques[i : i + TECHNIQUES_PER_BATCH]
                    for i in range(0, len(selected_techniques), TECHNIQUES_PER_BATCH)
                ]

                per_technique_cases = []

                for batch_index, batch in enumerate(batches, start=1):
                    st.write(
                        f"🧪 **Stage 3** — batch {batch_index}/{len(batches)}: "
                        f"{', '.join(batch)}..."
                    )

                    if batch_index > 1:
                        time.sleep(6)

                    cases, _raw = _stage_with_retry(
                        lambda hint, b=batch: generate_testcases_for_techniques(
                            requirement_json,
                            b,
                            test_case_format,
                            llm_config,
                            retry_hint=hint,
                        ),
                        status,
                        f"Test case generation (batch {batch_index}/{len(batches)})",
                    )

                    if cases is None:
                        st.warning(
                            f"⚠️ Skipping batch {batch_index}: no valid JSON after "
                            f"{JSON_RETRIES} attempts."
                        )
                        continue

                    per_technique_cases.extend(
                        group_rows_by_technique(cases, batch)
                    )

                test_cases = merge_technique_testcases(per_technique_cases)

                if not test_cases:
                    status.update(
                        label="❌ Test case generation failed", state="error"
                    )
                    st.error("No test cases were generated for any technique.")
                    st.stop()
            else:
                # No technique flags survived parsing — fall back to the
                # single batch prompt so the run still completes.
                st.write("No techniques flagged — using the standard prompt.")
                try:
                    test_cases, testcases_raw = _stage_with_retry(
                        lambda hint: generate_testcases(
                            requirement_json,
                            technique_json,
                            test_case_format,
                            llm_config,
                            retry_hint=hint,
                        ),
                        status,
                        "Test case generation",
                    )
                except LLMError as exc:
                    status.update(label="❌ Test case generation failed", state="error")
                    st.error(f"❌ {exc}")
                    st.stop()

                if test_cases is None:
                    status.update(label="❌ Test case generation failed", state="error")
                    st.error(
                        f"Test case generation returned invalid JSON after "
                        f"{JSON_RETRIES} attempts. Please try again."
                    )
                    with st.expander("View raw model output"):
                        st.code(testcases_raw)
                    st.stop()

                if isinstance(test_cases, dict):
                    test_cases = [test_cases]

            usage_sections.append(
                ("Stage 3 - Test Case Generation", llm_mod.usage_log()[usage_mark:])
            )

            if not test_cases:
                status.update(label="⚠️ No test cases generated", state="error")
                st.warning("No test cases were generated. Try refining the acceptance criteria.")
                st.stop()

            # ---- Stage 4: Excel Export ----
            st.write("📊 **Stage 4** — Building Excel workbook...")
            Path("output").mkdir(exist_ok=True)
            output_path = Path("output") / "TestCases.xlsx"
            generate_excel(test_cases, output_path, test_case_format)

            with open(output_path, "rb") as f:
                excel_bytes = f.read()

            status.update(label="✅ Test cases generated successfully", state="complete")

        # Persist results so they survive reruns (e.g. after download click)
        account_limits = (
            llm_mod.fetch_provider_limits(llm_config)
            if provider == "openrouter" and api_key
            else None
        )

        log_text = _build_generation_log(
            usage_sections, story_title, test_case_format, account_limits
        )

        st.session_state["results"] = {
            "requirement_json": requirement_json,
            "technique_json": technique_json,
            "test_cases": test_cases,
            "excel_bytes": excel_bytes,
            "log_bytes": log_text.encode("utf-8"),
            "format": test_case_format,
        }


# ==========================================================
# Results (rendered from session_state so they persist)
# ==========================================================

if "results" in st.session_state:

    results = st.session_state["results"]
    test_cases = results["test_cases"]

    st.markdown("---")
    section_title("📊", "Results")

    # ----- Metrics row -----
    m1, m2, m3 = st.columns(3)
    m1.metric("Test Cases", len(test_cases))
    m2.metric("Format", results["format"])
    m3.metric("Techniques Applied", count_applicable_techniques(results["technique_json"]))

    st.markdown("")

    # ----- Download -----
    st.download_button(
        label="📥 Download Test Cases (Excel)",
        data=results["excel_bytes"],
        file_name="TestCases.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    if results.get("log_bytes"):
        st.download_button(
            label="📄 Download Generation Log (model · tokens used · quota remaining)",
            data=results["log_bytes"],
            file_name="Generation_Log.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown("")

    # ----- Tabbed detail views -----
    tab_cases, tab_req, tab_tech = st.tabs([
        "📋 Test Cases",
        "🧩 Requirement Analysis",
        "🎯 Selected Techniques"
    ])

    with tab_cases:
        st.dataframe(test_cases, use_container_width=True)

    with tab_req:
        st.json(results["requirement_json"])

    with tab_tech:
        st.json(results["technique_json"])


# ==========================================================
# Footer — Stats & Quote
# ==========================================================

st.markdown(
    """
    <div class="footer-container">
        <div class="footer-stats">
            <div class="stat-badge">⚡ Speed 1Tera Hetz</div>
            <div class="stat-badge">💾 Memory 1Zita Byte</div>
        </div>
        <div class="footer-quote">✈️ TestCraft Goo — Powered by Innovation</div>
    </div>
    """,
    unsafe_allow_html=True
)
