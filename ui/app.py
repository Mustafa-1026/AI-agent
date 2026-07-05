"""
UI/app.py

Streamlit front-end for the AI Academic Intelligence System.

Flow:
    1. Landing page — choose Student or Professor.
    2. Professor must enter Name + Email before continuing.
       Student may optionally enter a name.
    3. Each role gets its own dashboard, calling ONLY into the
       existing backend (rag/retriever.py, agents/student_agent.py,
       agents/professor_agent.py). No embeddings, ChromaDB search, or
       ranking logic is reimplemented here.

Every backend call is wrapped defensively so a missing/broken module
degrades gracefully instead of crashing the whole app.
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root (parent of ui/) is importable regardless of
# where `streamlit run` is launched from. This is what was causing
# "No module named 'agents'" — Streamlit's working directory was `ui/`,
# not the project root, so `agents/`, `rag/`, `tools/` weren't on sys.path.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# ---------------------------------------------------------------------------
# Defensive backend imports
# ---------------------------------------------------------------------------

RETRIEVER_AVAILABLE = True
STUDENT_AGENT_AVAILABLE = True
PROFESSOR_AGENT_AVAILABLE = True

retriever_import_error = ""
student_import_error = ""
professor_import_error = ""

try:
    from rag.retriever import initialize_retriever
except Exception as exc:  # noqa: BLE001
    RETRIEVER_AVAILABLE = False
    retriever_import_error = str(exc)

try:
    from agents.student_agent import handle_student_query, generate_email_draft
except Exception as exc:  # noqa: BLE001
    STUDENT_AGENT_AVAILABLE = False
    student_import_error = str(exc)

try:
    from agents.professor_agent import (
        handle_professor_query,
        explain_collaboration_recommendation,
        generate_professor_email_draft,
        send_professor_email,
    )
except Exception as exc:  # noqa: BLE001
    PROFESSOR_AGENT_AVAILABLE = False
    professor_import_error = str(exc)


# ---------------------------------------------------------------------------
# Page config + global styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Academic Intelligence System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        #MainMenu, footer, header {visibility: hidden;}

        .hero {
            text-align: center;
            padding: 2.5rem 1rem 1.5rem 1rem;
        }
        .hero h1 {
            font-size: 2.6rem;
            font-weight: 800;
            background: linear-gradient(90deg, #6366F1, #EC4899);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.25rem;
        }
        .hero p {
            font-size: 1.05rem;
            color: #9CA3AF;
            max-width: 640px;
            margin: 0 auto;
        }

        .role-card {
            border: 1px solid rgba(120,120,120,0.25);
            border-radius: 16px;
            padding: 1.75rem 1.5rem;
            text-align: center;
            transition: all 0.15s ease-in-out;
        }
        .role-card h2 {
            font-size: 2.2rem;
            margin-bottom: 0.25rem;
        }
        .role-card p {
            color: #9CA3AF;
            font-size: 0.9rem;
        }

        .badge {
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
            background: rgba(99,102,241,0.15);
            color: #818CF8;
            margin-bottom: 0.4rem;
        }

        .score-badge {
            display: inline-block;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: 700;
        }
        .score-high { background: rgba(34,197,94,0.15); color: #22C55E; }
        .score-mid  { background: rgba(234,179,8,0.15); color: #EAB308; }
        .score-low  { background: rgba(239,68,68,0.15); color: #EF4444; }

        .status-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .status-ok { background: #22C55E; }
        .status-bad { background: #EF4444; }

        section[data-testid="stSidebar"] {
            border-right: 1px solid rgba(120,120,120,0.15);
        }

        div[data-testid="stButton"] > button {
            border-radius: 10px;
            font-weight: 600;
        }

        div[data-testid="stChatMessage"] {
            border-radius: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def init_session_state() -> None:
    defaults = {
        "stage": "landing",       # landing -> student_login / professor_login -> student_app / professor_app
        "student_name": "",
        "professor_name": "",
        "professor_email": "",
        "selected_faculty_id": None,
        "last_student_result": None,
        "last_professor_result": None,
        "student_chat_history": [],  # list of {"role": "user"/"assistant", "content": str, "result": dict|None}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


@st.cache_resource(show_spinner="Connecting to the faculty knowledge base...")
def get_retriever_context():
    if not RETRIEVER_AVAILABLE:
        return None
    try:
        return initialize_retriever()
    except Exception:
        return None


def go_to(stage: str) -> None:
    st.session_state["stage"] = stage
    st.rerun()


def reset_to_landing() -> None:
    st.session_state["stage"] = "landing"
    st.session_state["selected_faculty_id"] = None
    st.session_state["last_student_result"] = None
    st.session_state["last_professor_result"] = None
    st.session_state["student_chat_history"] = []
    st.rerun()


def score_badge_html(score: float) -> str:
    try:
        s = float(score)
    except (TypeError, ValueError):
        s = 0.0
    css_class = "score-high" if s >= 0.75 else "score-mid" if s >= 0.5 else "score-low"
    return f'<span class="score-badge {css_class}">Match {s:.2f}</span>'


# ---------------------------------------------------------------------------
# Sidebar — shown on every stage
# ---------------------------------------------------------------------------

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🎓 AI Academic\nIntelligence System")
        st.caption("Multi-agent faculty matching & research strategy")
        st.markdown("---")

        st.markdown("**System Status**")

        rag_ctx = get_retriever_context() if RETRIEVER_AVAILABLE else None
        rag_ok = RETRIEVER_AVAILABLE and rag_ctx is not None

        def status_line(label: str, ok: bool, detail: str = "") -> None:
            dot_class = "status-ok" if ok else "status-bad"
            text = "Online" if ok else "Unavailable"
            st.markdown(
                f'<span class="status-dot {dot_class}"></span>{label}: **{text}**',
                unsafe_allow_html=True,
            )
            if not ok and detail:
                st.caption(detail[:120])

        status_line("RAG Pipeline", RETRIEVER_AVAILABLE, retriever_import_error)
        status_line("ChromaDB", rag_ok, "Knowledge base not connected.")
        status_line("Student Agent", STUDENT_AGENT_AVAILABLE, student_import_error)
        status_line("Professor Agent", PROFESSOR_AGENT_AVAILABLE, professor_import_error)

        st.markdown("---")
        stage = st.session_state["stage"]
        if stage not in ("landing",):
            if st.button("← Back to Home", use_container_width=True, key="sidebar_home"):
                reset_to_landing()

        with st.expander("About this system"):
            st.write(
                "This system matches students with faculty mentors using "
                "semantic search over a ChromaDB knowledge base, and helps "
                "professors surface research trends, gaps, and collaboration "
                "opportunities across departments."
            )


# ---------------------------------------------------------------------------
# LANDING PAGE
# ---------------------------------------------------------------------------

def render_landing() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>🎓 AI Academic Intelligence System</h1>
            <p>Matches students with the right faculty mentors based on research
            interests, and helps professors analyze research trends, gaps, and
            collaboration opportunities across departments.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown(
            """
            <div class="role-card">
                <div class="badge">FOR STUDENTS</div>
                <h2>🎓</h2>
                <p>Find faculty mentors, explore project ideas, and draft
                outreach emails.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Continue as Student", use_container_width=True, key="landing_student"):
            go_to("student_login")

    with col2:
        st.markdown(
            """
            <div class="role-card">
                <div class="badge">FOR FACULTY</div>
                <h2>👨‍🏫</h2>
                <p>Discover research trends, identify gaps, and find
                collaboration partners.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")
        if st.button("Continue as Professor", use_container_width=True, key="landing_professor"):
            go_to("professor_login")


# ---------------------------------------------------------------------------
# STUDENT LOGIN (lightweight — name optional)
# ---------------------------------------------------------------------------

def render_student_login() -> None:
    st.markdown("### 🎓 Welcome, Student")
    st.caption("Tell us your name so we can personalize outreach emails for you.")

    with st.form("student_login_form"):
        name = st.text_input("Your name", value=st.session_state["student_name"], placeholder="e.g. Aarav Mehta")
        submitted = st.form_submit_button("Enter Student Dashboard", use_container_width=True)

    if submitted:
        st.session_state["student_name"] = name.strip()
        go_to("student_app")

    if st.button("← Back", key="student_login_back"):
        go_to("landing")


# ---------------------------------------------------------------------------
# PROFESSOR LOGIN (name + email required)
# ---------------------------------------------------------------------------

def render_professor_login() -> None:
    st.markdown("### 👨‍🏫 Welcome, Professor")
    st.caption("Please enter your details to continue — these are used to sign your outreach emails.")

    with st.form("professor_login_form"):
        name = st.text_input("Full name", value=st.session_state["professor_name"], placeholder="e.g. Dr. Kavita Rao")
        email = st.text_input("Email address", value=st.session_state["professor_email"], placeholder="e.g. kavita.rao@college.edu")
        submitted = st.form_submit_button("Enter Professor Dashboard", use_container_width=True)

    if submitted:
        clean_name = name.strip()
        clean_email = email.strip()
        if not clean_name:
            st.error("Please enter your name.")
        elif "@" not in clean_email or "." not in clean_email.split("@")[-1]:
            st.error("Please enter a valid email address.")
        else:
            st.session_state["professor_name"] = clean_name
            st.session_state["professor_email"] = clean_email
            go_to("professor_app")

    if st.button("← Back", key="professor_login_back"):
        go_to("landing")


# ---------------------------------------------------------------------------
# Shared helper — faculty match card with selection
# ---------------------------------------------------------------------------

def render_faculty_card(faculty: dict, index: int, key_prefix: str) -> bool:
    """Renders a faculty card with a 'Select' button. Returns True if clicked."""
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1.3])
        with col1:
            st.markdown(f"**{faculty.get('name', 'Unknown')}**")
            st.caption(faculty.get("institution", ""))
        with col2:
            st.write(faculty.get("department", "Unknown"))
        with col3:
            score = faculty.get("final_score", faculty.get("score", 0.0))
            st.markdown(score_badge_html(score), unsafe_allow_html=True)
        with col4:
            return st.button(
                "Select ✉️",
                key=f"{key_prefix}_{faculty.get('faculty_id', index)}",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# STUDENT DASHBOARD (chat-style)
# ---------------------------------------------------------------------------

SUGGESTED_STUDENT_PROMPTS = [
    "Need a mentor in AI",
    "Who works on NLP?",
    "Suggest a project in ML",
]


def render_student_result(result: dict, msg_index: int) -> None:
    """Renders faculty matches / warnings / projects for one chat turn."""
    top_matches = result.get("top_matches", [])
    warnings = result.get("warnings", [])
    explanations = result.get("explanations", [])
    projects = result.get("projects", [])
    best_recommendation = result.get("best_recommendation", "")

    if warnings:
        for warning_text in warnings:
            st.warning(warning_text)
    else:
        st.success("Strong alignment found between your query and top matches.")

    if not top_matches:
        st.info("No matching faculty were found for this query.")
        return

    st.markdown("**🏆 Top Faculty Matches**")
    for idx, faculty in enumerate(top_matches, start=1):
        clicked = render_faculty_card(faculty, idx, key_prefix=f"student_select_{msg_index}")
        if clicked:
            st.session_state["selected_faculty_id"] = faculty.get("faculty_id")
            st.session_state["_selected_result_index"] = msg_index

    if best_recommendation:
        st.info(f"**Best recommendation:** {best_recommendation}")

    selected_id = st.session_state.get("selected_faculty_id")
    if selected_id and st.session_state.get("_selected_result_index") == msg_index:
        selected_faculty = next((f for f in top_matches if f.get("faculty_id") == selected_id), None)
        if selected_faculty:
            st.markdown(f"**✉️ {selected_faculty.get('name')} — Details & Email Draft**")

            explanation = next((e for e in explanations if e.get("faculty_id") == selected_id), None)
            if explanation:
                with st.expander("Why this match?", expanded=True):
                    for reason in explanation.get("why_it_works", []):
                        st.write(f"✅ {reason}")
                    for reason in explanation.get("why_partial", []):
                        st.write(f"➖ {reason}")
                    for reason in explanation.get("missing_alignment", []):
                        st.write(f"⚠️ {reason}")

            if STUDENT_AGENT_AVAILABLE:
                try:
                    draft_text = generate_email_draft(selected_faculty, purpose="")
                    st.code(draft_text, language=None)
                    st.caption("Copy this draft using the icon above — emails are never sent automatically.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not generate email draft: {exc}")

    if projects:
        with st.expander("💡 Project Suggestions"):
            for project in projects:
                with st.container(border=True):
                    st.markdown(f"**{project.get('title', 'Untitled Project')}**")
                    st.write(project.get("description", ""))
                    st.caption(f"Related faculty: {project.get('related_faculty', 'Unknown')}")


def run_student_query(query: str) -> None:
    st.session_state["student_chat_history"].append({"role": "user", "content": query, "result": None})

    if not STUDENT_AGENT_AVAILABLE:
        st.session_state["student_chat_history"].append(
            {"role": "assistant", "content": f"Student agent is currently unavailable. Details: {student_import_error}", "result": None}
        )
        return

    context = get_retriever_context()
    if context is None:
        st.session_state["student_chat_history"].append(
            {
                "role": "assistant",
                "content": "Could not connect to the faculty knowledge base. Make sure the ChromaDB collection has been built, then try again.",
                "result": None,
            }
        )
        return

    try:
        result = handle_student_query(query, context=context)
        st.session_state["student_chat_history"].append(
            {"role": "assistant", "content": None, "result": result}
        )
        st.session_state["last_student_result"] = result
    except Exception as exc:  # noqa: BLE001
        st.session_state["student_chat_history"].append(
            {"role": "assistant", "content": f"Something went wrong while processing your query: {exc}", "result": None}
        )


def render_student_app() -> None:
    top_bar_l, top_bar_r = st.columns([5, 1])
    with top_bar_l:
        display_name = st.session_state["student_name"] or "Student"
        st.markdown(f"#### 🎓 Welcome, {display_name}")
    with top_bar_r:
        if st.button("Log out", key="student_logout"):
            reset_to_landing()

    st.caption("Ask about faculty mentors, research areas, or project ideas.")

    # Suggested prompt chips (only shown before first message)
    if not st.session_state["student_chat_history"]:
        chip_cols = st.columns(len(SUGGESTED_STUDENT_PROMPTS))
        for col, prompt in zip(chip_cols, SUGGESTED_STUDENT_PROMPTS):
            with col:
                if st.button(prompt, key=f"chip_{prompt}", use_container_width=True):
                    with st.spinner("Searching faculty knowledge base..."):
                        run_student_query(prompt)
                    st.rerun()

    # Render chat history
    for i, turn in enumerate(st.session_state["student_chat_history"]):
        role = turn["role"]
        with st.chat_message("user" if role == "user" else "assistant"):
            if turn.get("result") is not None:
                render_student_result(turn["result"], msg_index=i)
            else:
                st.write(turn["content"])

    # Chat input pinned at bottom
    query = st.chat_input("Ask your academic query, e.g. 'Who works on NLP?'")
    if query:
        with st.spinner("Searching faculty knowledge base..."):
            run_student_query(query)
        st.rerun()


# ---------------------------------------------------------------------------
# PROFESSOR DASHBOARD (tabbed)
# ---------------------------------------------------------------------------

def render_professor_app() -> None:
    top_bar_l, top_bar_r = st.columns([5, 1])
    with top_bar_l:
        st.markdown(f"#### 👨‍🏫 Welcome, {st.session_state['professor_name']}")
        st.caption(st.session_state["professor_email"])
    with top_bar_r:
        if st.button("Log out", key="professor_logout"):
            reset_to_landing()

    st.caption(
        "Examples: \"What are trending research areas?\" · "
        "\"Who can I collaborate with on Machine Learning?\" · "
        "\"What gaps exist in my department?\""
    )

    query = st.text_input("Ask your research-strategy query", key="professor_query")
    analyze_clicked = st.button("Analyze", type="primary", key="professor_analyze")

    if analyze_clicked:
        if not query or not query.strip():
            st.warning("Please enter a query before analyzing.")
        elif not PROFESSOR_AGENT_AVAILABLE:
            st.error(f"Professor agent is currently unavailable. Details: {professor_import_error}")
        else:
            context = get_retriever_context()
            if context is None:
                st.error(
                    "Could not connect to the faculty knowledge base. Make sure "
                    "the ChromaDB collection has been built, then try again."
                )
            else:
                try:
                    with st.spinner("Analyzing embeddings and research landscape..."):
                        result = handle_professor_query(
                            query,
                            context=context,
                            sender_name=st.session_state["professor_name"],
                        )
                    st.session_state["last_professor_result"] = result
                    st.session_state["selected_faculty_id"] = None
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Something went wrong while processing your query: {exc}")

    result = st.session_state.get("last_professor_result")
    if not result:
        return

    candidates = result.get("candidates", [])
    collaboration_matches = result.get("collaboration_matches", [])
    research_trends = result.get("research_trends", {})
    research_gaps = result.get("research_gaps", [])
    warnings = result.get("warnings", [])
    project_suggestions = result.get("project_suggestions", [])

    for warning_text in warnings:
        st.warning(warning_text)

    tab_matches, tab_collab, tab_insights = st.tabs(
        ["🌐 Faculty Matches", "🤝 Collaboration Graph", "📈 Research Insights"]
    )

    # ---- Tab 1: Faculty Matches ----
    with tab_matches:
        st.caption("Click **Select ✉️** on a faculty member to draft a collaboration email.")

        if not candidates:
            st.info("No faculty candidates found for this query.")
        else:
            for idx, faculty in enumerate(candidates, start=1):
                clicked = render_faculty_card(faculty, idx, key_prefix="professor_select")
                if clicked:
                    st.session_state["selected_faculty_id"] = faculty.get("faculty_id")

        selected_id = st.session_state.get("selected_faculty_id")
        if selected_id:
            selected_faculty = next((f for f in candidates if f.get("faculty_id") == selected_id), None)
            if selected_faculty:
                st.markdown("---")
                st.markdown(f"### ✉️ Draft Email to {selected_faculty.get('name')}")

                shared_topic = st.text_input(
                    "Shared research topic to mention (optional)",
                    key="professor_shared_topic",
                    placeholder="e.g. Federated Learning",
                )
                purpose = st.text_input(
                    "Purpose (optional)",
                    key="professor_email_purpose",
                    placeholder="e.g. explore a joint grant proposal",
                )

                if PROFESSOR_AGENT_AVAILABLE:
                    try:
                        draft = generate_professor_email_draft(
                            recipient=selected_faculty,
                            sender_name=st.session_state["professor_name"],
                            shared_topic=shared_topic.strip(),
                            purpose=purpose.strip(),
                        )
                        st.code(draft.get("body", ""), language=None)

                        confirmed = st.checkbox(
                            "I have reviewed this draft and confirm I want to send it",
                            key="professor_email_confirm",
                        )
                        if st.button("Send Email", key="professor_email_send"):
                            if not confirmed:
                                st.warning("Please confirm the checkbox above before sending.")
                            else:
                                send_result = send_professor_email(draft, confirm=True)
                                if send_result.get("status") == "sent":
                                    st.success(send_result.get("message", "Email sent."))
                                else:
                                    st.error(send_result.get("message", "Email could not be sent."))
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not generate/send email draft: {exc}")
                else:
                    st.error(f"Professor agent is currently unavailable. Details: {professor_import_error}")

    # ---- Tab 2: Collaboration Graph ----
    with tab_collab:
        if collaboration_matches:
            for pair in collaboration_matches:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{pair.get('faculty_1')} ↔ {pair.get('faculty_2')}**")
                        if PROFESSOR_AGENT_AVAILABLE:
                            try:
                                st.write(explain_collaboration_recommendation(pair))
                            except Exception as exc:  # noqa: BLE001
                                st.caption(f"Could not load explanation: {exc}")
                    with c2:
                        synergy = pair.get("synergy_score", pair.get("score"))
                        if synergy is not None:
                            st.markdown(score_badge_html(synergy), unsafe_allow_html=True)
        else:
            st.info("No strong collaboration pairs found for this query.")

        if project_suggestions:
            st.markdown("#### 💡 Joint Project Suggestions")
            for project in project_suggestions:
                with st.container(border=True):
                    st.markdown(f"**{project.get('title', 'Untitled Project')}**")
                    st.write(project.get("description", ""))

    # ---- Tab 3: Research Insights ----
    with tab_insights:
        st.markdown("#### 📈 Research Trends")
        if research_trends.get("available"):
            st.success("External trend data (via Tavily)")
            st.write(research_trends.get("raw_summary", ""))
        else:
            st.info("External trend search is unavailable right now — showing internal dataset only.")
            if candidates:
                seen_areas = set()
                for faculty in candidates:
                    for area in faculty.get("extracted", {}).get("research_areas", []):
                        seen_areas.add(area)
                if seen_areas:
                    st.write("Research areas currently represented in your dataset:")
                    st.write(", ".join(sorted(seen_areas)))

        st.markdown("#### 🔍 Research Gap Analysis")
        if research_gaps:
            for gap in research_gaps:
                st.write(f"- {gap}")
        else:
            st.info("No confirmed research gaps to show for this query.")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

render_sidebar()

stage = st.session_state["stage"]

if stage == "landing":
    render_landing()
elif stage == "student_login":
    render_student_login()
elif stage == "professor_login":
    render_professor_login()
elif stage == "student_app":
    render_student_app()
elif stage == "professor_app":
    render_professor_app()
else:
    st.session_state["stage"] = "landing"
    st.rerun()