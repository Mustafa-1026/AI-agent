"""
<<<<<<< HEAD
router.py
=========

Intent Router for the AI Faculty Intelligence &
Research Discovery System.

Responsibilities
----------------
- Classify user queries
- Route to the correct workflow

This module NEVER:
- Queries ChromaDB
- Generates embeddings
- Calls any LLM
"""

from __future__ import annotations

import re


# ----------------------------------------------------
# Intent Labels
# ----------------------------------------------------

FACULTY_SEARCH = "faculty_search"
FACULTY_DETAIL = "faculty_detail"
PROJECT_SUGGESTION = "project_suggestion"
COMPARISON = "comparison"
COLLABORATION = "collaboration_request"
UNKNOWN = "unknown"


# ----------------------------------------------------
# Keyword Dictionaries
# ----------------------------------------------------

PROJECT_KEYWORDS = [
    "project",
    "idea",
    "research topic",
    "suggest",
    "proposal",
]

DETAIL_KEYWORDS = [
    "tell me about",
    "details",
    "profile",
    "who is",
    "information",
]

COMPARE_KEYWORDS = [
    "compare",
    "difference",
    "better",
    "versus",
    "vs",
]

COLLABORATION_KEYWORDS = [
    "collaboration",
    "collaborate",
    "work together",
    "partner",
]

SEARCH_KEYWORDS = [
    "find",
    "search",
    "looking for",
    "who works on",
    "expert in",
    "faculty",
]


# ----------------------------------------------------
# Utility
# ----------------------------------------------------

def _contains_any(text: str, keywords: list[str]) -> bool:
    """
    Returns True if any keyword exists inside text.
    """

    text = text.lower()

    for keyword in keywords:
        if keyword in text:
            return True

    return False


# ----------------------------------------------------
# Intent Classifier
# ----------------------------------------------------

def classify_query(query: str) -> str:
    """
    Classify a user query into one of the supported intents.

    Returns:
        faculty_search
        faculty_detail
        project_suggestion
        comparison
        collaboration_request
        unknown
    """

    query = query.strip().lower()

    if not query:
        return UNKNOWN

    if _contains_any(query, PROJECT_KEYWORDS):
        return PROJECT_SUGGESTION

    if _contains_any(query, DETAIL_KEYWORDS):
        return FACULTY_DETAIL

    if _contains_any(query, COMPARE_KEYWORDS):
        return COMPARISON

    if _contains_any(query, COLLABORATION_KEYWORDS):
        return COLLABORATION

    if _contains_any(query, SEARCH_KEYWORDS):
        return FACULTY_SEARCH

    return FACULTY_SEARCH


# ----------------------------------------------------
# Helper Functions
# ----------------------------------------------------

def is_faculty_query(query: str) -> bool:
    return classify_query(query) == FACULTY_SEARCH


def is_detail_query(query: str) -> bool:
    return classify_query(query) == FACULTY_DETAIL


def is_project_query(query: str) -> bool:
    return classify_query(query) == PROJECT_SUGGESTION


def is_comparison_query(query: str) -> bool:
    return classify_query(query) == COMPARISON


def is_collaboration_query(query: str) -> bool:
    return classify_query(query) == COLLABORATION


# ----------------------------------------------------
# Testing
# ----------------------------------------------------

if __name__ == "__main__":

    while True:

        query = input("\nEnter Query: ")

        if query.lower() == "exit":
            break

        print("Intent:", classify_query(query))
=======
agents/router.py

Central cognitive orchestration engine for the multi-agent academic
intelligence system.

This module is a DETERMINISTIC TASK SCHEDULER. It never talks to
ChromaDB directly, never computes embeddings, and never hardcodes
faculty/student business logic. It only:

    1. Normalizes the incoming query
    2. Classifies intent
    3. Selects a deterministic module execution plan
    4. Dispatches to agents / intelligence modules / tools as black boxes
    5. Merges outputs into a strict, predictable response contract

The RetrieverContext is a process-wide singleton, initialized once and
reused across every request.
"""

from __future__ import annotations

import logging
import re
import time
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from rag.retriever import initialize_retriever, RetrieverContext

from agents.student_agent import handle_student_query
from agents.professor_agent import handle_professor_query

from agents.recommendation_engine import recommend
from agents.collaboration import analyze_collaboration
from agents.compatibility import check_compatibility
from agents.gap_analysis import analyze_gap
from agents.project_suggestions import suggest_projects
from agents.faculty_search import search_faculty

from tools.email_tool import generate_outreach_email
from tools.collaboration_engine import run_collaboration_engine
from tools.gap_analyzer import run_gap_analyzer
from tools.tavily_tool import fetch_external_trends


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

logger = logging.getLogger("router")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] [router] [%(levelname)s] %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# --------------------------------------------------------------------------- #
# Retriever Singleton (MANDATORY, process-wide, thread-safe)
# --------------------------------------------------------------------------- #

_retriever_lock = threading.Lock()
_retriever_context: Optional[RetrieverContext] = None


def get_retriever_context() -> RetrieverContext:
    """
    Return the process-wide RetrieverContext singleton.

    The retriever is initialized exactly once for the lifetime of the
    process and reused across all subsequent requests. It is never
    reinitialized per query.
    """
    global _retriever_context
    if _retriever_context is None:
        with _retriever_lock:
            if _retriever_context is None:  # double-checked locking
                logger.info("Initializing RetrieverContext singleton...")
                _retriever_context = initialize_retriever()
                logger.info("RetrieverContext singleton initialized.")
    return _retriever_context


# --------------------------------------------------------------------------- #
# Intent Classification
# --------------------------------------------------------------------------- #

INTENT_STUDENT = "student"
INTENT_PROFESSOR = "professor"
INTENT_RESEARCH_STRATEGY = "research_strategy"
INTENT_COLLABORATION = "collaboration"
INTENT_HYBRID = "hybrid"

VALID_INTENTS = {
    INTENT_STUDENT,
    INTENT_PROFESSOR,
    INTENT_RESEARCH_STRATEGY,
    INTENT_COLLABORATION,
    INTENT_HYBRID,
}

# Keyword triggers per intent (deterministic, no ML classification needed).
_INTENT_KEYWORDS: Dict[str, List[str]] = {
    INTENT_STUDENT: [
        "best professor",
        "mentorship",
        "mentor",
        "internship",
        "project idea",
        "project ideas",
        "email faculty",
        "who should i work with",
        "who should i work",
        "which professor",
        "guide me",
    ],
    INTENT_PROFESSOR: [
        "faculty research",
        "department analysis",
        "publication trend",
        "publication trends",
        "expertise mapping",
        "faculty profile",
        "faculty expertise",
    ],
    INTENT_RESEARCH_STRATEGY: [
        "research gap",
        "research gaps",
        "future trend",
        "future trends",
        "hot topic",
        "hot topics",
        "unsolved problem",
        "unsolved problems",
        "emerging area",
        "emerging areas",
    ],
    INTENT_COLLABORATION: [
        "collaboration",
        "synergy",
        "joint work",
        "co-author",
        "coauthor",
        "co author",
        "teamwork among faculty",
        "team up",
        "partner with",
    ],
}

# Order matters only for tie-breaking readability; scoring handles priority.
_INTENT_PRIORITY_ORDER = [
    INTENT_STUDENT,
    INTENT_PROFESSOR,
    INTENT_RESEARCH_STRATEGY,
    INTENT_COLLABORATION,
]


def normalize_query(query: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation noise."""
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    normalized = query.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def classify_intent(normalized_query: str) -> Tuple[str, float, Dict[str, List[str]]]:
    """
    Classify intent deterministically via keyword matching.

    Returns:
        (intent, confidence, matched_keywords_by_intent)

    If matches are found across multiple intent categories, the
    result is INTENT_HYBRID and matched_keywords_by_intent contains
    every category that matched (used downstream to build a merged
    execution plan).
    """
    matches: Dict[str, List[str]] = {}

    for intent, keywords in _INTENT_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in normalized_query]
        if hits:
            matches[intent] = hits

    if not matches:
        # No explicit trigger matched -> default to research_strategy
        # as the safest general-purpose academic-intelligence fallback.
        return INTENT_RESEARCH_STRATEGY, 0.35, {}

    if len(matches) == 1:
        intent = next(iter(matches))
        # Confidence scales with number of keyword hits, capped at 0.95.
        confidence = min(0.6 + 0.1 * len(matches[intent]), 0.95)
        return intent, confidence, matches

    # Multiple distinct intent categories triggered -> hybrid.
    total_hits = sum(len(v) for v in matches.values())
    confidence = min(0.5 + 0.05 * total_hits, 0.9)
    return INTENT_HYBRID, confidence, matches


# --------------------------------------------------------------------------- #
# Module Execution Plans
# --------------------------------------------------------------------------- #
#
# Each plan is a list of step names in deterministic execution order.
# Steps are resolved to callables in _STEP_DISPATCH below. This keeps
# the router acting as a scheduler: it decides WHAT runs and in WHAT
# order, while treating every module/tool as an opaque black box.

_EXECUTION_PLANS: Dict[str, List[str]] = {
    INTENT_STUDENT: [
        "student_agent",
        "recommendation_engine",
        "project_suggestions",
        "email_tool",
    ],
    INTENT_PROFESSOR: [
        "professor_agent",
        "faculty_search",
        "compatibility",
    ],
    INTENT_RESEARCH_STRATEGY: [
        "gap_analysis",
        "tavily_tool",
        "recommendation_engine",
    ],
    INTENT_COLLABORATION: [
        "collaboration",
        "compatibility",
        "professor_agent",
    ],
}


def _refine_plan_for_query(intent: str, normalized_query: str, base_plan: List[str]) -> List[str]:
    """
    Apply fine-grained scheduling rules on top of the base intent plan,
    matching the explicit examples in the specification:

      - "project idea"   -> student_agent, recommendation_engine, project_suggestions
      - "research gap"   -> gap_analysis, tavily_tool, professor_agent (enrichment)
      - "best professor" -> faculty_search, compatibility, recommendation_engine
    """
    plan = list(base_plan)

    if "project idea" in normalized_query and intent == INTENT_STUDENT:
        plan = ["student_agent", "recommendation_engine", "project_suggestions"]
        if "email" in normalized_query:
            plan.append("email_tool")

    if "research gap" in normalized_query and intent == INTENT_RESEARCH_STRATEGY:
        plan = ["gap_analysis", "tavily_tool", "professor_agent"]

    if "best professor" in normalized_query and intent == INTENT_STUDENT:
        plan = ["faculty_search", "compatibility", "recommendation_engine"]

    return plan


def build_execution_plan(
    intent: str, normalized_query: str, matched: Dict[str, List[str]]
) -> List[str]:
    """
    Build the ordered, deduplicated list of steps to execute for a
    given intent. For hybrid intent, merges the plans of every
    matched sub-intent while preserving priority order and removing
    duplicate steps.
    """
    if intent == INTENT_HYBRID:
        merged: List[str] = []
        for sub_intent in _INTENT_PRIORITY_ORDER:
            if sub_intent in matched:
                sub_plan = _refine_plan_for_query(
                    sub_intent, normalized_query, _EXECUTION_PLANS[sub_intent]
                )
                for step in sub_plan:
                    if step not in merged:
                        merged.append(step)
        return merged

    base_plan = _EXECUTION_PLANS.get(intent, _EXECUTION_PLANS[INTENT_RESEARCH_STRATEGY])
    return _refine_plan_for_query(intent, normalized_query, base_plan)


# --------------------------------------------------------------------------- #
# Step Dispatch Table (black-box adapters)
# --------------------------------------------------------------------------- #
#
# Each adapter receives (query, normalized_query, context, shared_state)
# and returns a dict payload. Adapters must never raise uncaught
# exceptions to the scheduler -- failures are caught and logged by
# _execute_step, allowing the router to degrade gracefully.

def _step_student_agent(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    result = handle_student_query(query, context=ctx)
    state["student_profile"] = result
    return result


def _step_professor_agent(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    result = handle_professor_query(query, context=ctx)
    state["professor_profile"] = result
    return result


def _step_recommendation_engine(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    return recommend(query=query, context=ctx, state=state)


def _step_collaboration(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    return analyze_collaboration(query=query, context=ctx, state=state)


def _step_compatibility(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    return check_compatibility(query=query, context=ctx, state=state)


def _step_gap_analysis(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    result = analyze_gap(query=query, context=ctx, state=state)
    # Optional dedicated tool-level enrichment, kept separate from
    # the intelligence-module layer per architecture rules.
    try:
        tool_result = run_gap_analyzer(query=query, context=ctx)
        result = {**result, "tool_enrichment": tool_result}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("gap_analyzer tool failed: %s", exc)
    return result


def _step_project_suggestions(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    return suggest_projects(query=query, context=ctx, state=state)


def _step_faculty_search(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    result = search_faculty(query=query, context=ctx)
    state["faculty_candidates"] = result
    return result


def _step_email_tool(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    target = state.get("faculty_candidates") or state.get("student_profile")
    return generate_outreach_email(query=query, context=ctx, target=target)


def _step_tavily_tool(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    return fetch_external_trends(query=query)


def _step_collaboration_engine_tool(query: str, nq: str, ctx: RetrieverContext, state: Dict[str, Any]) -> Dict[str, Any]:
    return run_collaboration_engine(query=query, context=ctx, state=state)


_STEP_DISPATCH: Dict[str, Callable[[str, str, RetrieverContext, Dict[str, Any]], Dict[str, Any]]] = {
    "student_agent": _step_student_agent,
    "professor_agent": _step_professor_agent,
    "recommendation_engine": _step_recommendation_engine,
    "collaboration": _step_collaboration,
    "compatibility": _step_compatibility,
    "gap_analysis": _step_gap_analysis,
    "project_suggestions": _step_project_suggestions,
    "faculty_search": _step_faculty_search,
    "email_tool": _step_email_tool,
    "tavily_tool": _step_tavily_tool,
    "collaboration_engine_tool": _step_collaboration_engine_tool,
}


def _execute_step(
    step_name: str,
    query: str,
    normalized_query: str,
    ctx: RetrieverContext,
    state: Dict[str, Any],
    execution_path: List[Dict[str, Any]],
) -> None:
    """
    Execute a single scheduler step with failure isolation, timing,
    and execution-trace logging.
    """
    adapter = _STEP_DISPATCH.get(step_name)
    trace_entry: Dict[str, Any] = {"step": step_name}
    start = time.monotonic()

    if adapter is None:
        trace_entry.update(status="skipped", reason="unknown_step")
        execution_path.append(trace_entry)
        logger.warning("Unknown step requested: %s", step_name)
        return

    try:
        output = adapter(query, normalized_query, ctx, state)
        state.setdefault("results", {})[step_name] = output
        trace_entry.update(status="success", duration_ms=round((time.monotonic() - start) * 1000, 2))
        logger.info("Step '%s' executed successfully.", step_name)
    except Exception as exc:
        trace_entry.update(
            status="failed",
            error=str(exc),
            duration_ms=round((time.monotonic() - start) * 1000, 2),
        )
        state.setdefault("results", {})[step_name] = {"error": str(exc)}
        logger.error("Step '%s' failed: %s", step_name, exc)

    execution_path.append(trace_entry)


# --------------------------------------------------------------------------- #
# Simple in-memory query cache (optional smart feature)
# --------------------------------------------------------------------------- #

_CACHE_TTL_SECONDS = 300
_query_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_cache_lock = threading.Lock()


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    with _cache_lock:
        entry = _query_cache.get(key)
        if not entry:
            return None
        timestamp, payload = entry
        if time.monotonic() - timestamp > _CACHE_TTL_SECONDS:
            _query_cache.pop(key, None)
            return None
        return payload


def _cache_set(key: str, payload: Dict[str, Any]) -> None:
    with _cache_lock:
        _query_cache[key] = (time.monotonic(), payload)


# --------------------------------------------------------------------------- #
# Core Public API
# --------------------------------------------------------------------------- #

def route_query(query: str, mode: str = "auto") -> Dict[str, Any]:
    """
    Route a raw user query through the academic intelligence system.

    Args:
        query: Raw natural-language user query.
        mode: "auto" for automatic intent classification, or an explicit
              intent override ("student", "professor",
              "research_strategy", "collaboration", "hybrid").

    Returns:
        Strict response contract:
        {
            "query": str,
            "intent": str,
            "modules_used": list,
            "result": dict,
            "metadata": {
                "routing_confidence": float,
                "context_initialized": bool,
                "execution_path": list
            }
        }
    """
    if not query or not query.strip():
        raise ValueError("query must be a non-empty string")

    normalized_query = normalize_query(query)

    cache_key = f"{mode}:{normalized_query}"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info("Cache hit for query: %r", query)
        return cached

    # 1. Ensure the retriever singleton exists (never reinitialized per query).
    ctx = get_retriever_context()
    context_initialized = ctx is not None

    # 2. Classify intent (respecting explicit mode override).
    matched: Dict[str, List[str]] = {}
    if mode != "auto":
        if mode not in VALID_INTENTS:
            raise ValueError(
                f"Invalid mode '{mode}'. Must be one of {sorted(VALID_INTENTS)} or 'auto'."
            )
        intent = mode
        confidence = 1.0
        if intent == INTENT_HYBRID:
            # Recompute matches so a forced hybrid mode still gets a
            # sensible merged plan.
            _, _, matched = classify_intent(normalized_query)
    else:
        intent, confidence, matched = classify_intent(normalized_query)

    # 3. Build deterministic module execution plan.
    plan = build_execution_plan(intent, normalized_query, matched)

    # 4. Execute plan as a task scheduler, treating every module as a black box.
    shared_state: Dict[str, Any] = {"query": query, "normalized_query": normalized_query}
    execution_path: List[Dict[str, Any]] = []

    for step_name in plan:
        _execute_step(step_name, query, normalized_query, ctx, shared_state, execution_path)

    # 5. Merge outputs.
    result = shared_state.get("results", {})

    response: Dict[str, Any] = {
        "query": query,
        "intent": intent,
        "modules_used": plan,
        "result": result,
        "metadata": {
            "routing_confidence": round(confidence, 2),
            "context_initialized": context_initialized,
            "execution_path": execution_path,
        },
    }

    _cache_set(cache_key, response)
    return response


# --------------------------------------------------------------------------- #
# Module smoke-test (not executed on import)
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    logging.getLogger("router").setLevel(logging.DEBUG)
    sample_queries = [
        "Who is the best professor for my project ideas in NLP?",
        "What are the current research gaps in federated learning?",
        "Find faculty for collaboration and synergy on a joint co-author paper.",
        "Show me department analysis and publication trends for the CS faculty.",
    ]
    for q in sample_queries:
        try:
            print(route_query(q))
        except Exception as e:  # pragma: no cover
            print(f"Error routing query {q!r}: {e}")
>>>>>>> 4f974ce3939c63fc1f0b0a87d767ee3065425c2c
