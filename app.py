import os
from pathlib import Path

import streamlit as st

from src.document_loader import (
    read_pdf,
    read_docx,
    read_txt
)
from src.requirement_analyzer import analyze_requirements
from src.technique_selector import select_techniques
from src.testcase_generator import generate_testcases
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
from src.llm import LLMConfig, LLMError, test_connection

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
                        "Free keys: Gemini → aistudio.google.com · Groq → console.groq.com"
                    )
                    api_provider = st.selectbox(
                        "Provider",
                        options=["gemini", "groq"],
                        format_func=lambda p: {
                            "gemini": "🌍 Google Gemini (free tier)",
                            "groq": "⚡ Groq (free tier)",
                        }[p],
                        key="signup_api_provider",
                    )
                    api_model = st.text_input(
                        "Model",
                        value="gemini-2.5-flash"
                        if api_provider == "gemini"
                        else "llama-3.3-70b-versatile",
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

    engine_choice = st.radio(
        "Engine",
        options=["🖥️ Local (Ollama)", "🌐 Online (Saved API Key)"],
        label_visibility="collapsed",
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
            options=["gemini", "groq"],
            format_func=lambda p: {
                "gemini": "🌍 Google Gemini (free tier)",
                "groq": "⚡ Groq (free tier)",
            }[p],
            key="key_provider",
            index=0 if (current_user.get("api_provider") or "gemini") == "gemini" else 1,
        )

        key_default_model = (
            "gemini-2.5-flash" if key_provider == "gemini" else "llama-3.3-70b-versatile"
        )

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

        with st.status("Running generation pipeline...", expanded=True) as status:

            # ---- Stage 1: Requirement Analysis ----
            st.write("🔍 **Stage 1** — Analyzing requirements...")
            try:
                requirement_raw = analyze_requirements(complete_context, llm_config)
            except LLMError as exc:
                status.update(label="❌ Requirement analysis failed", state="error")
                st.error(f"❌ {exc}")
                st.stop()
            requirement_json = validate_json(requirement_raw)

            if requirement_json is None:
                status.update(label="❌ Requirement analysis failed", state="error")
                st.error("Requirement analysis returned invalid JSON. Please try again.")
                with st.expander("View raw model output"):
                    st.code(requirement_raw)
                st.stop()

            # ---- Stage 2: Technique Selection ----
            st.write("🎯 **Stage 2** — Selecting testing techniques...")
            try:
                technique_raw = select_techniques(requirement_json, llm_config)
            except LLMError as exc:
                status.update(label="❌ Technique selection failed", state="error")
                st.error(f"❌ {exc}")
                st.stop()
            technique_json = validate_json(technique_raw)

            if technique_json is None:
                status.update(label="❌ Technique selection failed", state="error")
                st.error("Technique selection returned invalid JSON. Please try again.")
                with st.expander("View raw model output"):
                    st.code(technique_raw)
                st.stop()

            # ---- Stage 3: Test Case Generation ----
            st.write("🧪 **Stage 3** — Generating test cases...")
            try:
                testcases_raw = generate_testcases(
                    requirement_json,
                    technique_json,
                    test_case_format,
                    llm_config,
                )
            except LLMError as exc:
                status.update(label="❌ Test case generation failed", state="error")
                st.error(f"❌ {exc}")
                st.stop()
            test_cases = validate_json(testcases_raw)

            if test_cases is None:
                status.update(label="❌ Test case generation failed", state="error")
                st.error("Test case generation returned invalid JSON. Please try again.")
                with st.expander("View raw model output"):
                    st.code(testcases_raw)
                st.stop()

            if isinstance(test_cases, dict):
                test_cases = [test_cases]

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
        st.session_state["results"] = {
            "requirement_json": requirement_json,
            "technique_json": technique_json,
            "test_cases": test_cases,
            "excel_bytes": excel_bytes,
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
