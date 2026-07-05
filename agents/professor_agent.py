"""
professor_agent.py
===================

Professor Mode (Research Strategy Mode) Agent for the AI-powered
Faculty Intelligence & Research Discovery System.

Role
----
This module is a reasoning / decision-making layer built ON TOP OF the
existing RAG retrieval pipeline and the four tools in tools/. It does
NOT modify, bypass, or duplicate retrieval logic, and it does NOT call
any LLM. The only ways this module touches data are:

    context = initialize_retriever()
    results = semantic_search(query, context=context)          # rag/retriever.py
    find_collaborations(faculty_list)                           # tools/collaboration_engine.py
    analyze_gaps(faculty_list, trending_topics)                 # tools/gap_analyzer.py
    search_trends(query)                                        # tools/tavily_tool.py
    compose_email(...) / send_email(..., confirm=True)          # tools/email_tool.py

Everything else — cross-college discovery, collaboration synergy
scoring, gap-analysis orchestration, project suggestions, devil's
advocate warnings, and email drafting — is deterministic, rule-based
logic grounded strictly in what those calls return. This module never
invents faculty, research areas, skills, or projects that are not
present in retrieved/tool data.

Shared utilities reused from student_agent.py
-----------------------------------------------
`rank_and_score()`, `devil_advocate_filter()`, and
`_extract_document_fields()` are generic RAG-quality utilities (not
student-specific despite their file location), so they are imported
and reused here rather than duplicated. If their implementation
changes in student_agent.py, professor_agent.py picks up the change
automatically.

This is NOT a chatbot. It is a research-strategy decision engine for
faculty: cross-college discovery, collaboration matching, and
trend/gap analysis.

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from rag.retriever import RetrieverContext, semantic_search
from agents.student_agent import (
    rank_and_score,
    devil_advocate_filter,
    _extract_document_fields,
)

from tools.collaboration_engine import find_collaborations
from tools.gap_analyzer import analyze_gaps
from tools.tavily_tool import search_trends
from tools.email_tool import compose_email, send_email


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default number of candidates to pull from RAG before diversifying
#: by institution for cross-college discovery.
DEFAULT_RETRIEVE_TOP_K: int = 12

#: Default number of cross-college candidates surfaced to the caller.
DEFAULT_TOP_CANDIDATES: int = 6

#: Default number of trending topics to extract from a Tavily response.
DEFAULT_MAX_TOPICS: int = 5

#: Default number of project suggestions generated per query.
DEFAULT_PROJECT_COUNT: int = 3

#: Strings returned by tools/tavily_tool.py on failure — used to detect
#: a failed trend lookup instead of treating the error text as data.
_TAVILY_ERROR_PREFIXES = (
    "Tavily API key not found",
    "Tavily API error",
)


# ---------------------------------------------------------------------------
# 1. Intent classification (professor / research-strategy variant)
# ---------------------------------------------------------------------------

def classify_professor_intent(query: str) -> str:
    """
    Classify a professor's research-strategy query into one of five
    structured intent labels using rule-based keyword matching.

    Intent labels:
        - "collaboration_matching": looking for potential collaborators
          (e.g. "find someone to collaborate with on...").
        - "trend_analysis": wants current research trend information
          (e.g. "what's trending in...", "latest developments in...").
        - "gap_analysis": wants to know what topics aren't yet covered
          by existing faculty (e.g. "what research gaps exist in...").
        - "project_suggestion": wants project/proposal ideas.
        - "faculty_search": the default — cross-college discovery of
          faculty matching a topic.

    Args:
        query: The raw professor query text.

    Returns:
        One of: "faculty_search", "collaboration_matching",
        "trend_analysis", "gap_analysis", "project_suggestion".
    """
    if not query or not query.strip():
        return "faculty_search"

    lowered = query.strip().lower()

    collaboration_keywords = [
        "collaborate", "collaboration", "co-author", "coauthor",
        "partner with", "joint research", "find a collaborator",
        "work together", "synergy", "email", "send email", "reach out",
        "contact", "write to", "message",
    ]
    if any(keyword in lowered for keyword in collaboration_keywords):
        return "collaboration_matching"

    trend_keywords = [
        "trend", "trending", "latest research", "latest developments",
        "current state of", "what's new in", "emerging",
    ]
    if any(keyword in lowered for keyword in trend_keywords):
        return "trend_analysis"

    gap_keywords = [
        "gap", "gaps", "not covered", "missing research", "underexplored",
        "unexplored", "what are we missing",
    ]
    if any(keyword in lowered for keyword in gap_keywords):
        return "gap_analysis"

    project_keywords = [
        "project idea", "project ideas", "proposal", "suggest a project",
        "grant idea", "funding proposal",
    ]
    if any(keyword in lowered for keyword in project_keywords):
        return "project_suggestion"

    return "faculty_search"


# ---------------------------------------------------------------------------
# 2. Cross-college faculty discovery (USP #4)
# ---------------------------------------------------------------------------

def discover_cross_college_faculty(
    query: str,
    context: RetrieverContext,
    top_k: int = DEFAULT_TOP_CANDIDATES,
) -> List[Dict[str, Any]]:
    """
    Retrieve and rank faculty candidates for a research-strategy query,
    diversified across institutions so results aren't dominated by a
    single college.

    Args:
        query: The professor's natural-language query.
        context: An initialized RetrieverContext.
        top_k: Maximum number of diversified candidates to return.
            Defaults to DEFAULT_TOP_CANDIDATES (6).

    Returns:
        A list of ranked, enriched result dictionaries (same shape as
        student_agent.rank_and_score() output), with at most one
        top-ranked entry per institution, ordered by final_score
        descending. Empty list on failure or no results.
    """
    if not query or not query.strip():
        print("[professor_agent.py] WARNING: Empty query supplied to discover_cross_college_faculty().")
        return []

    raw_results = semantic_search(query=query, context=context, top_k=DEFAULT_RETRIEVE_TOP_K)
    ranked_results = rank_and_score(raw_results, query)

    seen_institutions: set = set()
    diversified: List[Dict[str, Any]] = []

    for result in ranked_results:
        institution = result.get("institution", "Unknown")
        if institution in seen_institutions:
            continue
        seen_institutions.add(institution)
        diversified.append(result)
        if len(diversified) >= top_k:
            break

    return diversified


# ---------------------------------------------------------------------------
# 3. Research trend analysis (USP #5)
# ---------------------------------------------------------------------------

def _is_tavily_error(response_text: str) -> bool:
    """
    Determine whether a string returned by search_trends() represents
    a failure rather than actual trend content.

    Args:
        response_text: The raw string returned by
            tools.tavily_tool.search_trends().

    Returns:
        True if the text matches a known Tavily error pattern.
    """
    if not response_text:
        return True
    return any(response_text.startswith(prefix) for prefix in _TAVILY_ERROR_PREFIXES)


def _parse_topics_from_trend_text(text: str, max_topics: int = DEFAULT_MAX_TOPICS) -> List[str]:
    """
    Extract a rough list of candidate topic phrases from free-form
    trend text returned by Tavily, for use as gap-analysis input.

    This is a best-effort heuristic split (by newlines, bullets, and
    clause separators) over externally sourced text — it is NOT
    parsing structured faculty data, so imperfect splits only affect
    the granularity of gap analysis, not faculty-data accuracy.

    Args:
        text: Raw trend summary text.
        max_topics: Maximum number of topic phrases to return.

    Returns:
        A list of short topic phrase strings, capped at max_topics.
    """
    if not text:
        return []

    # Prefer line/bullet splits if present, else fall back to commas/semicolons.
    candidates = [line.strip("-•* \t") for line in text.splitlines() if line.strip()]
    if len(candidates) <= 1:
        candidates = [part.strip() for part in text.replace(";", ",").split(",")]

    cleaned = []
    for candidate in candidates:
        candidate = candidate.strip().rstrip(".")
        if 3 <= len(candidate.split()) <= 8 and candidate not in cleaned:
            cleaned.append(candidate)

    return cleaned[:max_topics]


def get_research_trends(
    topic_query: str,
    max_topics: int = DEFAULT_MAX_TOPICS,
) -> Dict[str, Any]:
    """
    Fetch current research trend information for a topic via Tavily,
    and derive a rough list of candidate trending-topic phrases from
    it for downstream gap analysis.

    Args:
        topic_query: The topic/field to search trends for (e.g.
            "artificial intelligence research trends 2026").
        max_topics: Maximum number of topic phrases to extract.

    Returns:
        A dictionary:
            {
                "raw_summary": str,       # full Tavily response text
                "topics": List[str],      # extracted topic phrases
                "available": bool,        # False if Tavily call failed
            }
        Never raises — failures are reflected via "available": False
        and an explanatory "raw_summary".
    """
    if not topic_query or not topic_query.strip():
        return {"raw_summary": "", "topics": [], "available": False}

    try:
        response_text = search_trends(topic_query.strip())
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[professor_agent.py] ERROR: search_trends() failed: {exc}.")
        return {"raw_summary": "", "topics": [], "available": False}

    if _is_tavily_error(response_text):
        print(f"[professor_agent.py] WARNING: Trend lookup unavailable: {response_text}")
        return {"raw_summary": response_text, "topics": [], "available": False}

    topics = _parse_topics_from_trend_text(response_text, max_topics=max_topics)
    return {"raw_summary": response_text, "topics": topics, "available": True}


# ---------------------------------------------------------------------------
# Adapter — reshapes ranked RAG results into the flat structure that
# tools/collaboration_engine.py and tools/gap_analyzer.py expect.
# ---------------------------------------------------------------------------

def _adapt_for_tools(ranked_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Reshape ranked retriever results (which nest research areas inside
    "extracted") into the flat {"name": ..., "research_areas": [...]}
    structure expected by find_collaborations() and analyze_gaps().

    Research area strings are lowercased and stripped for consistent,
    case-insensitive matching in both downstream tools.

    Args:
        ranked_results: Output of student_agent.rank_and_score().

    Returns:
        A list of flat dictionaries:
            {"name": str, "faculty_id": str, "research_areas": List[str]}
    """
    adapted: List[Dict[str, Any]] = []
    for result in ranked_results:
        extracted = result.get("extracted", {})
        research_areas = [
            area.strip().lower()
            for area in extracted.get("research_areas", [])
            if area and area.strip()
        ]
        adapted.append(
            {
                "name": result.get("name", "Unknown"),
                "faculty_id": result.get("faculty_id", "Unknown"),
                "research_areas": research_areas,
            }
        )
    return adapted


# ---------------------------------------------------------------------------
# 4. Collaboration matching + synergy score (USP #8)
# ---------------------------------------------------------------------------

def find_collaboration_synergies(
    ranked_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Identify potential faculty collaboration pairs based on shared
    research areas, and attach a synergy score to each pair.

    Args:
        ranked_results: Ranked results from
            discover_cross_college_faculty() or rank_and_score().

    Returns:
        A list of dictionaries:
            {
                "faculty_1": str,
                "faculty_2": str,
                "shared_area": List[str],
                "synergy_score": float,   # 0.0-1.0
            }
        Empty list if fewer than 2 candidates or no shared areas exist.
    """
    if not ranked_results or len(ranked_results) < 2:
        return []

    adapted = _adapt_for_tools(ranked_results)

    try:
        raw_pairs = find_collaborations(adapted)
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[professor_agent.py] ERROR: find_collaborations() failed: {exc}.")
        return []

    # Build a lookup of each faculty's full research-area set (by name)
    # so we can compute a synergy score without re-deriving overlap logic.
    areas_by_name: Dict[str, set] = {
        item["name"]: set(item["research_areas"]) for item in adapted
    }

    enriched_pairs: List[Dict[str, Any]] = []
    for pair in raw_pairs:
        name_1 = pair.get("faculty_1", "")
        name_2 = pair.get("faculty_2", "")
        shared = set(pair.get("shared_area", []))

        areas_1 = areas_by_name.get(name_1, set())
        areas_2 = areas_by_name.get(name_2, set())
        union_size = len(areas_1 | areas_2)
        synergy_score = round(len(shared) / union_size, 4) if union_size else 0.0

        enriched_pairs.append(
            {
                "faculty_1": name_1,
                "faculty_2": name_2,
                "shared_area": pair.get("shared_area", []),
                "synergy_score": synergy_score,
            }
        )

    enriched_pairs.sort(key=lambda item: item["synergy_score"], reverse=True)
    return enriched_pairs


def explain_collaboration_recommendation(pair: Dict[str, Any]) -> str:
    """
    Produce a grounded, human-readable explanation for why a
    collaboration pair was recommended.

    Args:
        pair: A single enriched pair from find_collaboration_synergies().

    Returns:
        A one-sentence explanation string.
    """
    shared = pair.get("shared_area", [])
    if not shared:
        return (
            f"'{pair.get('faculty_1')}' and '{pair.get('faculty_2')}' were "
            f"paired, but no shared research areas were found in their "
            f"retrieved profiles."
        )
    return (
        f"'{pair.get('faculty_1')}' and '{pair.get('faculty_2')}' share "
        f"{len(shared)} research area(s) — {', '.join(shared)} — giving a "
        f"synergy score of {pair.get('synergy_score', 0.0):.2f}."
    )


# ---------------------------------------------------------------------------
# 5. Research gap analysis (USP #6)
# ---------------------------------------------------------------------------

def find_research_gaps(
    ranked_results: List[Dict[str, Any]],
    topic_query: str,
    max_topics: int = DEFAULT_MAX_TOPICS,
) -> Dict[str, Any]:
    """
    Identify research topics that are currently trending (per Tavily)
    but not covered by any of the retrieved faculty's listed research
    areas.

    Args:
        ranked_results: Ranked faculty results (from
            discover_cross_college_faculty() or rank_and_score()).
        topic_query: The broader field/topic to check trends for
            (e.g. "machine learning").
        max_topics: Maximum number of trending topics to consider.

    Returns:
        A dictionary:
            {
                "gaps": List[str],
                "trend_summary": str,
                "trends_available": bool,
            }
        "gaps" is empty if trend data is unavailable or no faculty
        were supplied — this is a genuine "unknown", not a claim that
        no gaps exist.
    """
    trend_info = get_research_trends(topic_query, max_topics=max_topics)

    if not trend_info["available"] or not ranked_results:
        return {
            "gaps": [],
            "trend_summary": trend_info["raw_summary"],
            "trends_available": trend_info["available"],
        }

    adapted = _adapt_for_tools(ranked_results)

    try:
        gaps = analyze_gaps(adapted, trend_info["topics"])
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[professor_agent.py] ERROR: analyze_gaps() failed: {exc}.")
        gaps = []

    return {
        "gaps": gaps,
        "trend_summary": trend_info["raw_summary"],
        "trends_available": True,
    }


# ---------------------------------------------------------------------------
# 6. Collaboration-aware project suggestions (USP #7)
# ---------------------------------------------------------------------------

def suggest_collaboration_projects(
    collaboration_pairs: List[Dict[str, Any]],
    max_projects: int = DEFAULT_PROJECT_COUNT,
) -> List[Dict[str, Any]]:
    """
    Generate joint-research project ideas grounded in the shared
    research areas of recommended collaboration pairs.

    Args:
        collaboration_pairs: Enriched pairs from
            find_collaboration_synergies().
        max_projects: Maximum number of project ideas to return.

    Returns:
        A list of dictionaries:
            {
                "title": str,
                "description": str,
                "related_faculty": List[str],
                "synergy_score": float,
            }
    """
    projects: List[Dict[str, Any]] = []

    for pair in collaboration_pairs:
        if len(projects) >= max_projects:
            break

        shared_areas = pair.get("shared_area", [])
        if not shared_areas:
            continue

        primary_area = shared_areas[0]
        projects.append(
            {
                "title": f"Joint Study on {primary_area.title()}",
                "description": (
                    f"A collaborative research project combining "
                    f"{pair.get('faculty_1')}'s and {pair.get('faculty_2')}'s "
                    f"shared expertise in {primary_area}."
                ),
                "related_faculty": [pair.get("faculty_1"), pair.get("faculty_2")],
                "synergy_score": pair.get("synergy_score", 0.0),
            }
        )

    return projects[:max_projects]


# ---------------------------------------------------------------------------
# 7. Professor-to-professor email drafting/sending
# ---------------------------------------------------------------------------

def generate_professor_email_draft(
    recipient: Dict[str, Any],
    sender_name: str = "",
    shared_topic: str = "",
    purpose: str = "",
) -> Dict[str, str]:
    """
    Compose a peer-tone collaboration email draft to another faculty
    member. This function only drafts — it never sends.

    Args:
        recipient: A single faculty result dict (must have "name").
        sender_name: The requesting professor's name, used to sign the
            email.
        shared_topic: A grounded shared research area (typically from
            find_collaboration_synergies()'s "shared_area" field) used
            to justify the outreach. If empty, a generic context line
            is used instead.
        purpose: Optional free-text purpose override.

    Returns:
        A composed email dictionary (see tools.email_tool.compose_email):
            {"to": str, "subject": str, "body": str,
             "relationship": str, "status": "drafted"}
    """
    recipient_name = recipient.get("name", "Colleague")
    recipient_email = recipient.get("metadata", {}).get("Email", "")

    context_line = (
        f"We both list {shared_topic} as a shared research interest, and I "
        f"believe our work could complement each other well."
        if shared_topic
        else "I believe there is meaningful alignment between our research worth exploring."
    )

    return compose_email(
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        sender_name=sender_name,
        relationship="professor_to_professor",
        context_line=context_line,
        shared_topic=shared_topic,
    )


def send_professor_email(draft: Dict[str, str], confirm: bool = False) -> Dict[str, str]:
    """
    Send a previously composed professor-to-professor email draft.
    Requires explicit confirmation — mirrors tools.email_tool.send_email's
    safety gate.

    Args:
        draft: A composed email dict from
            generate_professor_email_draft().
        confirm: Must be True (set only after human approval) for the
            email to actually be sent.

    Returns:
        The structured result dict from tools.email_tool.send_email().
    """
    return send_email(
        recipient_email=draft.get("to", ""),
        subject=draft.get("subject", ""),
        body=draft.get("body", ""),
        confirm=confirm,
    )


# ---------------------------------------------------------------------------
# Orchestration entry point
# ---------------------------------------------------------------------------

def handle_professor_query(
    query: str,
    context: RetrieverContext,
    sender_name: str = "",
    email_purpose: str = "",
) -> Dict[str, Any]:
    """
    End-to-end orchestration for Professor / Research Strategy Mode:
    classify intent, discover cross-college candidates, find
    collaboration synergies, analyze trends/gaps, suggest joint
    projects, flag weak matches, and (if relevant) draft a
    professor-to-professor email.

    Args:
        query: The professor's natural-language query.
        context: An initialized RetrieverContext, created ONCE by the
            caller and reused across queries.
        sender_name: The requesting professor's name (used only for
            email drafting).
        email_purpose: Optional free-text purpose override for an
            email draft, used only when intent is
            "collaboration_matching".

    Returns:
        A dictionary:
            {
                "intent": str,
                "candidates": List[Dict[str, Any]],
                "collaboration_matches": List[Dict[str, Any]],
                "research_trends": Dict[str, Any],
                "research_gaps": List[str],
                "warnings": List[str],
                "project_suggestions": List[Dict[str, Any]],
                "email_draft": Dict[str, str],
            }
    """
    intent = classify_professor_intent(query)

    candidates = discover_cross_college_faculty(query, context=context, top_k=DEFAULT_TOP_CANDIDATES)
    warnings = devil_advocate_filter(candidates, query)

    collaboration_matches: List[Dict[str, Any]] = []
    project_suggestions: List[Dict[str, Any]] = []
    research_trends: Dict[str, Any] = {"raw_summary": "", "topics": [], "available": False}
    research_gaps: List[str] = []
    email_draft: Dict[str, str] = {}

    if intent in ("collaboration_matching", "faculty_search", "project_suggestion") and candidates:
        collaboration_matches = find_collaboration_synergies(candidates)

    if intent == "project_suggestion" and collaboration_matches:
        project_suggestions = suggest_collaboration_projects(collaboration_matches, max_projects=DEFAULT_PROJECT_COUNT)

    if intent == "trend_analysis":
        research_trends = get_research_trends(query, max_topics=DEFAULT_MAX_TOPICS)

    if intent == "gap_analysis" and candidates:
        gap_result = find_research_gaps(candidates, query, max_topics=DEFAULT_MAX_TOPICS)
        research_gaps = gap_result["gaps"]
        research_trends = {
            "raw_summary": gap_result["trend_summary"],
            "topics": [],
            "available": gap_result["trends_available"],
        }

    if intent == "collaboration_matching" and collaboration_matches:
        best_pair = collaboration_matches[0]
        target_name = best_pair.get("faculty_2")
        target_candidate = next(
            (c for c in candidates if c.get("name") == target_name), None
        )
        if target_candidate:
            shared_topic = (
                best_pair.get("shared_area", [""])[0] if best_pair.get("shared_area") else ""
            )
            email_draft = generate_professor_email_draft(
                recipient=target_candidate,
                sender_name=sender_name,
                shared_topic=shared_topic,
                purpose=email_purpose,
            )

    return {
        "intent": intent,
        "candidates": candidates,
        "collaboration_matches": collaboration_matches,
        "research_trends": research_trends,
        "research_gaps": research_gaps,
        "warnings": warnings,
        "project_suggestions": project_suggestions,
        "email_draft": email_draft,
    }


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from rag.retriever import initialize_retriever

    retriever_context = initialize_retriever()

    if retriever_context is not None:
        sample_query = "Find collaborators for research in Machine Learning"
        response = handle_professor_query(
            sample_query, context=retriever_context, sender_name="Dr. Rao"
        )

        print(f"Intent: {response['intent']}")
        for candidate in response["candidates"]:
            print(f"- {candidate['name']} ({candidate['institution']})")
        for pair in response["collaboration_matches"]:
            print(explain_collaboration_recommendation(pair))
        for warning in response["warnings"]:
            print(warning)