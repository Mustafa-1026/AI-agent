"""
UI/app.py

Streamlit front-end for the AI Academic Intelligence System.

This file ONLY calls into the existing backend (rag/retriever.py,
agents/student_agent.py, agents/professor_agent.py). It does not
reimplement embeddings, ChromaDB search, or any NLP/ranking logic.
Every backend call is wrapped defensively so a missing/broken module
(e.g. an optional tool like Tavily or email) degrades gracefully
instead of crashing the app.
"""

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
        send_professor_email,
    )
except Exception as exc:  # noqa: BLE001
    PROFESSOR_AGENT_AVAILABLE = False
    professor_import_error = str(exc)


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Academic Intelligence System",
    page_icon="🎓",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Cached retriever context (loaded once per session)
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Connecting to the faculty knowledge base...")
def get_retriever_context():
    if not RETRIEVER_AVAILABLE:
        return None
    try:
        return initialize_retriever()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Sidebar — role selection
# ---------------------------------------------------------------------------

st.sidebar.title("AI Academic Intelligence System")
st.sidebar.markdown("Choose how you'd like to use the system:")

mode = st.sidebar.radio(
    "Mode",
    options=["Student Mode 🎓", "Professor Mode 👨‍🏫"],
    index=0,
    label_visibility="collapsed",
)

user_name = st.sidebar.text_input(
    "Your name (used to sign email drafts)",
    value="",
    placeholder="e.g. Aarav Mehta",
)

st.sidebar.divider()
st.sidebar.caption(
    "Backend status: "
    + ("🟢 Retriever" if RETRIEVER_AVAILABLE else "🔴 Retriever")
    + " · "
    + ("🟢 Student Agent" if STUDENT_AGENT_AVAILABLE else "🔴 Student Agent")
    + " · "
    + ("🟢 Professor Agent" if PROFESSOR_AGENT_AVAILABLE else "🔴 Professor Agent")
)


# ---------------------------------------------------------------------------
# Home header (always visible)
# ---------------------------------------------------------------------------

st.title("AI Academic Intelligence System")
st.write(
    "Matches students with the right faculty mentors based on research "
    "interests, and helps professors analyze research trends, gaps, and "
    "collaboration opportunities across departments."
)
st.divider()


# ---------------------------------------------------------------------------
# Shared helper — faculty match card
# ---------------------------------------------------------------------------

def render_faculty_card(faculty: dict, index: int) -> None:
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.markdown(f"**{index}. {faculty.get('name', 'Unknown')}**")
        st.caption(faculty.get("institution", ""))
    with col2:
        st.write(faculty.get("department", "Unknown"))
    with col3:
        score = faculty.get("final_score", faculty.get("score", 0.0))
        st.metric("Match", f"{score:.2f}")


# ---------------------------------------------------------------------------
# STUDENT MODE
# ---------------------------------------------------------------------------

def render_student_mode() -> None:
    st.subheader("🎓 Student Mode")
    st.caption(
        "Examples: \"Who works on NLP?\" · \"Suggest a project in AI\" · "
        "\"Who should I approach for ML?\""
    )

    query = st.text_input("Ask your academic query", key="student_query")
    search_clicked = st.button("Search", type="primary", key="student_search")

    if not search_clicked:
        return

    if not query or not query.strip():
        st.warning("Please enter a query before searching.")
        return

    if not STUDENT_AGENT_AVAILABLE:
        st.error(
            "Student agent is currently unavailable. "
            f"Details: {student_import_error}"
        )
        return

    context = get_retriever_context()
    if context is None:
        st.error(
            "Could not connect to the faculty knowledge base. Please make "
            "sure the ChromaDB collection has been built, then try again."
        )
        return

    try:
        with st.spinner("Searching faculty knowledge base..."):
            result = handle_student_query(query, context=context)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Something went wrong while processing your query: {exc}")
        return

    top_matches = result.get("top_matches", [])
    warnings = result.get("warnings", [])
    explanations = result.get("explanations", [])
    projects = result.get("projects", [])
    best_recommendation = result.get("best_recommendation", "")

    # --- Warnings first (core USP — devil's advocate) ---
    if warnings:
        for warning_text in warnings:
            st.warning(warning_text)
    else:
        st.success("Strong alignment found between your query and top matches.")

    # --- Top faculty matches ---
    st.markdown("### 🏆 Top Faculty Matches")
    if not top_matches:
        st.info("No matching faculty were found for this query.")
    else:
        for idx, faculty in enumerate(top_matches, start=1):
            with st.container(border=True):
                render_faculty_card(faculty, idx)

                explanation = next(
                    (e for e in explanations if e.get("faculty_id") == faculty.get("faculty_id")),
                    None,
                )
                if explanation:
                    with st.expander("Why this match?"):
                        for reason in explanation.get("why_it_works", []):
                            st.write(f"✅ {reason}")
                        for reason in explanation.get("why_partial", []):
                            st.write(f"➖ {reason}")
                        for reason in explanation.get("missing_alignment", []):
                            st.write(f"⚠️ {reason}")

                draft_key = f"draft_button_{faculty.get('faculty_id', idx)}"
                if st.button("✉️ Draft Email", key=draft_key):
                    try:
                        draft_text = generate_email_draft(faculty, purpose="")
                        st.text_area(
                            "Email draft (not sent — copy and send manually)",
                            value=draft_text,
                            height=220,
                            key=f"draft_text_{faculty.get('faculty_id', idx)}",
                        )
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not generate email draft: {exc}")

        if best_recommendation:
            st.info(f"**Best recommendation:** {best_recommendation}")

    # --- Project suggestions ---
    st.markdown("### 💡 Project Suggestions")
    if projects:
        for project in projects:
            with st.container(border=True):
                st.markdown(f"**{project.get('title', 'Untitled Project')}**")
                st.write(project.get("description", ""))
                st.caption(f"Related faculty: {project.get('related_faculty', 'Unknown')}")
    else:
        st.info("No project suggestions available for this query yet.")


# ---------------------------------------------------------------------------
# PROFESSOR MODE
# ---------------------------------------------------------------------------

def render_professor_mode() -> None:
    st.subheader("👨‍🏫 Professor Mode")
    st.caption(
        "Examples: \"What are trending research areas?\" · "
        "\"Who can I collaborate with?\" · \"What gaps exist in my department?\""
    )

    query = st.text_input("Ask your research-strategy query", key="professor_query")
    analyze_clicked = st.button("Analyze", type="primary", key="professor_analyze")

    if not analyze_clicked:
        return

    if not query or not query.strip():
        st.warning("Please enter a query before analyzing.")
        return

    if not PROFESSOR_AGENT_AVAILABLE:
        st.error(
            "Professor agent is currently unavailable. "
            f"Details: {professor_import_error}"
        )
        return

    context = get_retriever_context()
    if context is None:
        st.error(
            "Could not connect to the faculty knowledge base. Please make "
            "sure the ChromaDB collection has been built, then try again."
        )
        return

    try:
        with st.spinner("Analyzing research landscape..."):
            result = handle_professor_query(
                query, context=context, sender_name=user_name or ""
            )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Something went wrong while processing your query: {exc}")
        return

    candidates = result.get("candidates", [])
    collaboration_matches = result.get("collaboration_matches", [])
    research_trends = result.get("research_trends", {})
    research_gaps = result.get("research_gaps", [])
    warnings = result.get("warnings", [])
    project_suggestions = result.get("project_suggestions", [])
    email_draft = result.get("email_draft", {})

    for warning_text in warnings:
        st.warning(warning_text)

    # --- Candidates (cross-college discovery) ---
    st.markdown("### 🌐 Faculty Discovered Across Institutions")
    if candidates:
        for idx, faculty in enumerate(candidates, start=1):
            with st.container(border=True):
                render_faculty_card(faculty, idx)
    else:
        st.info("No faculty candidates found for this query.")

    # --- Trending vs internal comparison ---
    st.markdown("### 📈 Research Trends")
    if research_trends.get("available"):
        st.success("External trend data (via Tavily):")
        st.write(research_trends.get("raw_summary", ""))
    else:
        st.info(
            "External trend search is unavailable right now, so this is "
            "based on the internal faculty dataset only."
        )
        if candidates:
            seen_areas = set()
            for faculty in candidates:
                for area in faculty.get("extracted", {}).get("research_areas", []):
                    seen_areas.add(area)
            if seen_areas:
                st.write("Research areas currently represented in your dataset:")
                st.write(", ".join(sorted(seen_areas)))

    # --- Research gap analysis ---
    st.markdown("### 🔍 Research Gap Analysis")
    if research_gaps:
        for gap in research_gaps:
            st.write(f"- {gap}")
    else:
        st.info(
            "No confirmed research gaps to show — this requires external "
            "trend data or a broader candidate pool."
        )

    # --- Collaboration suggestions ---
    st.markdown("### 🤝 Collaboration Suggestions")
    if collaboration_matches:
        for pair in collaboration_matches:
            with st.container(border=True):
                st.markdown(
                    f"**{pair.get('faculty_1')} ↔ {pair.get('faculty_2')}**"
                )
                st.write(explain_collaboration_recommendation(pair))
    else:
        st.info("No strong collaboration pairs found for this query.")

    if project_suggestions:
        st.markdown("### 💡 Joint Project Suggestions")
        for project in project_suggestions:
            with st.container(border=True):
                st.markdown(f"**{project.get('title', 'Untitled Project')}**")
                st.write(project.get("description", ""))

    # --- Optional email draft (collaboration outreach) ---
    if email_draft:
        st.markdown("### ✉️ Collaboration Email Draft")
        st.text_area(
            "Draft (review before sending)",
            value=email_draft.get("body", ""),
            height=220,
            key="professor_email_draft",
        )
        confirmed = st.checkbox(
            "I have reviewed this draft and confirm I want to send it",
            key="professor_email_confirm",
        )
        if st.button("Send Email", key="professor_email_send"):
            if not confirmed:
                st.warning("Please confirm the checkbox above before sending.")
            else:
                try:
                    send_result = send_professor_email(email_draft, confirm=True)
                    if send_result.get("status") == "sent":
                        st.success(send_result.get("message", "Email sent."))
                    else:
                        st.error(send_result.get("message", "Email could not be sent."))
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not send email: {exc}")


# ---------------------------------------------------------------------------
# Mode dispatch
# ---------------------------------------------------------------------------

if mode.startswith("Student"):
    render_student_mode()
else:
    render_professor_mode()