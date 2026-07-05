"""
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

Note on priority order
-----------------------
Keyword checks below are ordered to match agents/student_agent.py's
classify_intent() (collaboration > comparison > detail > project >
search), so that if this router is ever wired into the pipeline in
place of the per-agent classifiers, results stay consistent instead
of silently diverging.
"""

from __future__ import annotations

from typing import List


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

COLLABORATION_KEYWORDS = [
    "collaboration",
    "collaborate",
    "work together",
    "partner",
    "mentor me",
    "guide me",
    "join their lab",
]

COMPARE_KEYWORDS = [
    "compare",
    "difference",
    "better",
    "versus",
    " vs ",
    "which one",
]

DETAIL_KEYWORDS = [
    "tell me about",
    "details",
    "profile",
    "who is",
    "information",
]

PROJECT_KEYWORDS = [
    "project idea",
    "project ideas",
    "research topic",
    "suggest a project",
    "proposal",
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

def _contains_any(text: str, keywords: List[str]) -> bool:
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
    query = (query or "").strip().lower()

    if not query:
        return UNKNOWN

    if _contains_any(query, COLLABORATION_KEYWORDS):
        return COLLABORATION

    if _contains_any(query, COMPARE_KEYWORDS):
        return COMPARISON

    if _contains_any(query, DETAIL_KEYWORDS):
        return FACULTY_DETAIL

    if _contains_any(query, PROJECT_KEYWORDS):
        return PROJECT_SUGGESTION

    if _contains_any(query, SEARCH_KEYWORDS):
        return FACULTY_SEARCH

    return FACULTY_SEARCH


# ----------------------------------------------------
# Public routing entry point
# ----------------------------------------------------

def route_query(query: str) -> str:
    """
    Public entry point matching the system spec's
    `agents.router.route_query()` contract. Currently a thin alias
    over classify_query() — kept as a separate name so callers don't
    depend on the internal classifier function name, and so this can
    be extended later (e.g. to dispatch to a handler function instead
    of just returning a label) without breaking callers.

    Args:
        query: The raw user query text.

    Returns:
        One of the intent label constants defined above.
    """
    return classify_query(query)


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