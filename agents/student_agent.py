<<<<<<< HEAD
from agents.project_suggestions import suggest_projects


def show_best_match(rag_results):

    if len(rag_results) == 0:
        print("No faculty found.")
        return

    current = 0

    while True:

        faculty = rag_results[current]

        print("\n==============================")
        print("FACULTY", current + 1)
        print("==============================")
        print("Name       :", faculty["name"])
        print("Department :", faculty["department"])
        print("Research   :", ", ".join(faculty["research_areas"]))
        print("Score      :", faculty["score"])

        # Show project suggestions
        suggest_projects(faculty)

        choice = input("\nType 'next' for another faculty or 'exit': ")

        if choice.lower() == "next":

            if current + 1 < len(rag_results):
                current += 1
            else:
                print("\nNo more faculty available.")

        elif choice.lower() == "exit":
            break

        else:
            print("Invalid input")


def tell_about_faculty(name, rag_results):

    for faculty in rag_results:

        if faculty["name"].lower() == name.lower():

            print("\n==============================")
            print("FACULTY DETAILS")
            print("==============================")
            print("Name       :", faculty["name"])
            print("Department :", faculty["department"])
            print("Research   :", ", ".join(faculty["research_areas"]))
            print("Score      :", faculty["score"])

            # Show projects here also
            suggest_projects(faculty)

            return

    print("Faculty not found.")


if __name__ == "__main__":

    rag_results = [

        {
            "name": "Dr. Ramesh Karnati",
            "department": "CSE",
            "research_areas": [
                "Artificial Intelligence",
                "Machine Learning"
            ],
            "score": 0.95
        },

        {
            "name": "Dr. Priya",
            "department": "CSE",
            "research_areas": [
                "Computer Vision",
                "Deep Learning"
            ],
            "score": 0.90
        },

        {
            "name": "Dr. Vinay",
            "department": "CSE",
            "research_areas": [
                "IoT",
                "Data Mining"
            ],
            "score": 0.87
        }

    ]

    show_best_match(rag_results)

    name = input("\nEnter faculty name: ")
    tell_about_faculty(name, rag_results)
=======
"""
student_agent.py
=================

Student Mode Agent for the AI-powered Faculty Intelligence & Research
Discovery System.

Role
----
This module is a reasoning / decision-making layer built ON TOP OF the
existing RAG retrieval pipeline. It does NOT modify, bypass, or
duplicate retrieval logic. The only way this module touches faculty
data is through:

    context = initialize_retriever()
    results = semantic_search(query, context=context)

Everything downstream — intent classification, ranking, explanations,
devil's-advocate warnings, project suggestions, and email drafts — is
computed with deterministic, rule-based logic grounded strictly in the
"document" and "metadata" fields that semantic_search() returns. This
module NEVER calls an LLM or any external API, and NEVER invents
faculty, skills, or projects that are not present in retrieved data.
This is a hard constraint, not a style choice: it is what keeps every
recommendation, warning, and email draft traceable back to real
retrieved evidence.

This is NOT a chatbot. It is an academic-advisor decision engine.

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from rag.retriever import RetrieverContext, semantic_search


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Below this final ranking score, a match is flagged by the devil's
#: advocate filter as a weak/poor fit.
MISMATCH_SCORE_THRESHOLD: float = 0.45

#: Below this keyword-overlap ratio, a match is considered to have weak
#: topical alignment with the query, regardless of raw semantic score.
WEAK_OVERLAP_THRESHOLD: float = 0.15

#: Default number of faculty to retrieve from RAG per query.
DEFAULT_RETRIEVE_TOP_K: int = 8

#: Default number of ranked matches surfaced to the caller.
DEFAULT_TOP_MATCHES: int = 5

#: Default number of project ideas to generate.
DEFAULT_PROJECT_COUNT: int = 3

#: Common English stopwords stripped out of queries before computing
#: keyword/skill overlap, so overlap scoring focuses on meaningful terms.
_STOPWORDS: set = {
    "a", "an", "the", "is", "are", "was", "were", "who", "what", "which",
    "for", "to", "of", "in", "on", "with", "and", "or", "i", "want",
    "looking", "find", "me", "please", "can", "you", "about", "tell",
    "compare", "vs", "versus", "better", "best", "good", "expert",
    "experts", "faculty", "professor", "professors", "researcher",
    "researchers", "works", "work", "working", "do", "does", "this",
    "that", "college", "department", "search", "show", "give", "some",
    "need", "help", "project", "projects", "idea", "ideas",
}

# Regex patterns matching the fixed sentence templates produced by
# embedder.create_document(). Extracting from these known templates
# keeps every derived fact grounded in the retrieved document text
# rather than guessed.
_PATTERNS: Dict[str, re.Pattern] = {
    "specialization": re.compile(
        r"specialization includes (.*?)\.", re.IGNORECASE
    ),
    "research_areas": re.compile(
        r"research interests include (.*?)\.", re.IGNORECASE
    ),
    "skills": re.compile(r"skills include (.*?)\.", re.IGNORECASE),
    "expertise_tags": re.compile(
        r"recognized for expertise in (.*?)\.", re.IGNORECASE
    ),
    "current_projects": re.compile(
        r"currently working on (.*?)\.", re.IGNORECASE
    ),
    "memberships": re.compile(r"a member of (.*?)\.", re.IGNORECASE),
    "awards": re.compile(r"awards include (.*?)\.", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# Text helpers — grounding extraction directly in retrieved document text
# ---------------------------------------------------------------------------

def _split_phrase_list(phrase: str) -> List[str]:
    """
    Split a natural-language "A, B and C" style phrase back into a
    list of individual items.

    Args:
        phrase: A comma/and-joined phrase, as produced by embedder.py's
            document generation (e.g. "Python, TensorFlow and SQL").

    Returns:
        A list of individual, stripped items. Empty list if the
        phrase is empty or is the "Information not available"
        placeholder.
    """
    if not phrase or phrase.strip().lower() == "information not available":
        return []

    cleaned = re.sub(r"\s+and\s+", ", ", phrase.strip())
    items = [item.strip().rstrip(".") for item in cleaned.split(",")]
    return [item for item in items if item]


def _extract_document_fields(document: str) -> Dict[str, List[str]]:
    """
    Parse a faculty's generated semantic document back into structured
    fields (research areas, skills, current projects, etc.) using the
    fixed sentence templates from embedder.create_document().

    This is the ONLY mechanism this module uses to recover structured
    facts about a faculty member beyond what's already in metadata —
    it never guesses or fabricates values.

    Args:
        document: The natural-language document text for one faculty
            member, as returned by semantic_search().

    Returns:
        A dictionary mapping field name -> list of extracted items.
        Fields not found in the document map to an empty list.
    """
    extracted: Dict[str, List[str]] = {}
    document = document or ""

    for field_name, pattern in _PATTERNS.items():
        match = pattern.search(document)
        extracted[field_name] = _split_phrase_list(match.group(1)) if match else []

    return extracted


def _tokenize(text: str) -> List[str]:
    """
    Lowercase and tokenize free text into meaningful keyword tokens,
    stripping punctuation and common stopwords.

    Args:
        text: Raw text (a query or a phrase from a document).

    Returns:
        A list of lowercase keyword tokens.
    """
    if not text:
        return []
    raw_tokens = re.findall(r"[a-zA-Z][a-zA-Z\-]*", text.lower())
    return [token for token in raw_tokens if token not in _STOPWORDS and len(token) > 1]


def _keyword_overlap_ratio(query_tokens: List[str], candidate_text: str) -> float:
    """
    Compute the fraction of query keyword tokens that appear
    (as substrings) somewhere in a candidate text blob.

    Args:
        query_tokens: Tokenized query keywords.
        candidate_text: The text to search within (e.g. combined
            research areas + skills + expertise tags for one faculty).

    Returns:
        A ratio between 0.0 and 1.0. Returns 0.0 if there are no query
        tokens to compare.
    """
    if not query_tokens:
        return 0.0
    candidate_lower = candidate_text.lower()
    matches = sum(1 for token in query_tokens if token in candidate_lower)
    return matches / len(query_tokens)


# ---------------------------------------------------------------------------
# 1. Intent classification
# ---------------------------------------------------------------------------

def classify_intent(query: str) -> str:
    """
    Classify a student's query into one of five structured intent
    labels using rule-based keyword matching.

    Intent labels:
        - "collaboration_request": the student wants to reach out to
          or work with a faculty member (e.g. mentions email, contact,
          collaborate, guidance, mentorship).
        - "comparison": the student wants two or more faculty compared
          (e.g. mentions "compare", "vs", "better than", "or").
        - "faculty_detail": the student wants details about a specific,
          named faculty member (e.g. "tell me about Dr. X").
        - "project_suggestion": the student wants project ideas.
        - "faculty_search": the default — a general semantic search
          for faculty matching some topic/skill.

    Args:
        query: The raw student query text.

    Returns:
        One of: "faculty_search", "faculty_detail",
        "project_suggestion", "comparison", "collaboration_request".
    """
    if not query or not query.strip():
        return "faculty_search"

    lowered = query.strip().lower()

    collaboration_keywords = [
        "collaborate", "collaboration", "email", "contact", "reach out",
        "write to", "mentor me", "guide me", "supervise", "work with",
        "join their lab", "join his lab", "join her lab", "mentorship",
    ]
    if any(keyword in lowered for keyword in collaboration_keywords):
        return "collaboration_request"

    comparison_keywords = ["compare", " vs ", "versus", "better than", "which one"]
    has_two_names_with_or = bool(re.search(r"\bdr\.?\s+\w+.*\bor\b.*\bdr\.?\s+\w+", lowered))
    if any(keyword in lowered for keyword in comparison_keywords) or has_two_names_with_or:
        return "comparison"

    detail_keywords = ["tell me about", "who is", "details of", "details about", "profile of"]
    if any(keyword in lowered for keyword in detail_keywords):
        return "faculty_detail"

    project_keywords = [
        "project idea", "project ideas", "suggest a project", "suggest projects",
        "what project", "build something", "final year project",
        "capstone", "suggest project",
    ]
    if any(keyword in lowered for keyword in project_keywords):
        return "project_suggestion"

    return "faculty_search"


# ---------------------------------------------------------------------------
# 2. Faculty retrieval (thin wrapper — never bypasses the retriever)
# ---------------------------------------------------------------------------

def retrieve_faculty(
    query: str,
    context: RetrieverContext,
    top_k: int = DEFAULT_RETRIEVE_TOP_K,
) -> List[Dict[str, Any]]:
    """
    Retrieve candidate faculty for a query via the existing RAG
    retriever. This is a thin wrapper — it performs no ranking logic
    of its own and never queries ChromaDB directly.

    Args:
        query: The student's natural-language query.
        context: An initialized RetrieverContext (from
            rag.retriever.initialize_retriever()).
        top_k: Number of candidates to pull from semantic search before
            downstream re-ranking. Defaults to DEFAULT_RETRIEVE_TOP_K.

    Returns:
        The raw list of result dictionaries from semantic_search().
        Empty list if retrieval fails or finds nothing.
    """
    if not query or not query.strip():
        print("[student_agent.py] WARNING: Empty query supplied to retrieve_faculty().")
        return []

    return semantic_search(query=query, context=context, top_k=top_k)


# ---------------------------------------------------------------------------
# 3. Ranking and scoring
# ---------------------------------------------------------------------------

def rank_and_score(
    results: List[Dict[str, Any]],
    query: str,
) -> List[Dict[str, Any]]:
    """
    Re-rank raw RAG results using a blended score of semantic
    similarity, skill/research keyword overlap, and department
    relevance — all computed strictly from the retrieved document and
    metadata (no external knowledge is introduced).

    Args:
        results: Raw results from retrieve_faculty()/semantic_search().
        query: The original student query, used to compute overlap.

    Returns:
        A new list of result dictionaries, each augmented with:
            - "extracted": structured fields parsed from the document
              (research_areas, skills, expertise_tags, current_projects,
              specialization, memberships, awards)
            - "skill_overlap": float 0.0-1.0
            - "department_match": bool
            - "final_score": blended float 0.0-1.0
        Sorted by "final_score" descending.
    """
    if not results:
        return []

    query_tokens = _tokenize(query)
    ranked: List[Dict[str, Any]] = []

    for result in results:
        document = result.get("document", "")
        extracted = _extract_document_fields(document)

        overlap_text = " ".join(
            extracted.get("research_areas", [])
            + extracted.get("skills", [])
            + extracted.get("expertise_tags", [])
            + extracted.get("specialization", [])
        )
        skill_overlap = _keyword_overlap_ratio(query_tokens, overlap_text)

        department = str(result.get("department", "")).lower()
        department_match = any(token in department for token in query_tokens) if query_tokens else False

        semantic_score = float(result.get("score", 0.0))

        final_score = (
            (semantic_score * 0.5)
            + (skill_overlap * 0.35)
            + ((1.0 if department_match else 0.0) * 0.15)
        )
        final_score = max(0.0, min(1.0, final_score))

        enriched = dict(result)
        enriched["extracted"] = extracted
        enriched["skill_overlap"] = round(skill_overlap, 4)
        enriched["department_match"] = department_match
        enriched["final_score"] = round(final_score, 4)
        ranked.append(enriched)

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return ranked


# ---------------------------------------------------------------------------
# 4. Explanations
# ---------------------------------------------------------------------------

def generate_explanations(
    faculty: List[Dict[str, Any]],
    query: str,
) -> List[Dict[str, Any]]:
    """
    Generate a grounded explanation for each ranked faculty match,
    describing why it works, why it only partially works, and what
    alignment factors are missing — using only fields already present
    in the retrieved/extracted data.

    Args:
        faculty: Ranked results as returned by rank_and_score().
        query: The original student query.

    Returns:
        A list of dictionaries, one per faculty member:
            {
                "faculty_id": str,
                "name": str,
                "why_it_works": [str, ...],
                "why_partial": [str, ...],
                "missing_alignment": [str, ...],
            }
    """
    query_tokens = set(_tokenize(query))
    explanations: List[Dict[str, Any]] = []

    for item in faculty:
        extracted = item.get("extracted", {})
        research_areas = extracted.get("research_areas", [])
        skills = extracted.get("skills", [])
        expertise_tags = extracted.get("expertise_tags", [])
        current_projects = extracted.get("current_projects", [])

        matched_research = [
            area for area in research_areas
            if any(token in area.lower() for token in query_tokens)
        ]
        matched_skills = [
            skill for skill in skills
            if any(token in skill.lower() for token in query_tokens)
        ]

        why_it_works: List[str] = []
        why_partial: List[str] = []
        missing_alignment: List[str] = []

        if matched_research:
            why_it_works.append(
                f"Research areas directly align: {', '.join(matched_research)}."
            )
        if matched_skills:
            why_it_works.append(
                f"Relevant technical skills: {', '.join(matched_skills)}."
            )
        if item.get("department_match"):
            why_it_works.append(
                f"Department '{item.get('department')}' matches the query context."
            )
        if current_projects and not matched_research and not matched_skills:
            why_partial.append(
                f"Current projects ({', '.join(current_projects)}) may be "
                f"tangentially related, but no direct research/skill overlap "
                f"was found."
            )
        if not why_it_works and expertise_tags:
            why_partial.append(
                f"Broader expertise tags present ({', '.join(expertise_tags)}), "
                f"but no exact topical match."
            )
        if not research_areas:
            missing_alignment.append("No research areas listed in the profile.")
        if not skills:
            missing_alignment.append("No skills listed in the profile.")
        if not matched_research and not matched_skills:
            missing_alignment.append(
                "No direct keyword overlap between the query and this "
                "faculty member's listed research areas or skills."
            )

        if not why_it_works and not why_partial:
            why_partial.append(
                "Matched primarily on general semantic similarity rather "
                "than explicit research/skill keywords."
            )

        explanations.append(
            {
                "faculty_id": item.get("faculty_id", "Unknown"),
                "name": item.get("name", "Unknown"),
                "why_it_works": why_it_works,
                "why_partial": why_partial,
                "missing_alignment": missing_alignment,
            }
        )

    return explanations


# ---------------------------------------------------------------------------
# 5. Devil's advocate filter (core USP feature)
# ---------------------------------------------------------------------------

def devil_advocate_filter(
    results: List[Dict[str, Any]],
    query: str,
    score_threshold: float = MISMATCH_SCORE_THRESHOLD,
    overlap_threshold: float = WEAK_OVERLAP_THRESHOLD,
) -> List[str]:
    """
    Critically evaluate the top-ranked matches and produce warnings
    whenever the best available options are a weak fit for the
    student's query — the system's core "devil's advocate" USP.

    Warnings are only generated when there is genuine evidence of a
    mismatch (low blended score, weak keyword overlap, or no
    department relevance for a department-specific-sounding query);
    this function never fabricates a warning about a faculty member
    without a grounded reason drawn from rank_and_score()'s output.

    Args:
        results: Ranked results, already scored by rank_and_score().
        query: The original student query.
        score_threshold: Final-score floor below which a match is
            flagged as weak. Defaults to MISMATCH_SCORE_THRESHOLD.
        overlap_threshold: Skill/research overlap floor below which a
            match is flagged as topically weak. Defaults to
            WEAK_OVERLAP_THRESHOLD.

    Returns:
        A list of human-readable warning strings. Empty list if the
        top match is a strong fit or there are no results at all.
    """
    if not results:
        return [
            "⚠ No matching faculty were found for this query. Try "
            "broadening your search terms or checking spelling of any "
            "named topics."
        ]

    warnings: List[str] = []
    top_match = results[0]
    top_score = top_match.get("final_score", 0.0)
    top_overlap = top_match.get("skill_overlap", 0.0)

    is_weak_score = top_score < score_threshold
    is_weak_overlap = top_overlap < overlap_threshold

    if is_weak_score or is_weak_overlap:
        warnings.append(
            f"⚠ '{top_match.get('name', 'This faculty member')}' is not an "
            f"ideal match for your query (confidence score: {top_score:.2f}). "
            f"The topical overlap with your search terms is weak."
        )

        better_alternative: Optional[Dict[str, Any]] = None
        for candidate in results[1:]:
            if candidate.get("skill_overlap", 0.0) > top_overlap:
                better_alternative = candidate
                break

        if better_alternative:
            warnings.append(
                f"👉 Better option: '{better_alternative.get('name')}' shows "
                f"stronger topical alignment (overlap score: "
                f"{better_alternative.get('skill_overlap', 0.0):.2f})."
            )
        else:
            warnings.append(
                "👉 No strongly aligned faculty were found in the current "
                "results. Consider refining your query with more specific "
                "keywords (e.g. a precise sub-field, tool, or technique) "
                "or searching a related department."
            )

    return warnings


# ---------------------------------------------------------------------------
# 6. Project suggestions
# ---------------------------------------------------------------------------

def suggest_projects(
    top_faculty: List[Dict[str, Any]],
    max_projects: int = DEFAULT_PROJECT_COUNT,
) -> List[Dict[str, Any]]:
    """
    Generate project ideas grounded strictly in retrieved faculty
    metadata: existing listed projects are preferred verbatim, and any
    synthesized idea is a direct combination of that faculty member's
    own listed research areas and skills — never an invented topic.

    Args:
        top_faculty: Ranked faculty results (from rank_and_score()),
            typically just the top 1-2 matches.
        max_projects: Maximum number of project ideas to return.
            Defaults to DEFAULT_PROJECT_COUNT (3).

    Returns:
        A list of dictionaries:
            {
                "title": str,
                "description": str,
                "related_faculty": str,
                "faculty_id": str,
            }
        Empty list if no faculty have enough information to ground a
        suggestion.
    """
    projects: List[Dict[str, Any]] = []

    for faculty in top_faculty:
        if len(projects) >= max_projects:
            break

        name = faculty.get("name", "Unknown")
        faculty_id = faculty.get("faculty_id", "Unknown")
        extracted = faculty.get("extracted", {})
        research_areas = extracted.get("research_areas", [])
        skills = extracted.get("skills", [])
        current_projects = extracted.get("current_projects", [])

        # Prefer faculty's own listed current projects — these are
        # real, already-vetted work, not synthesized combinations.
        for existing_project in current_projects:
            if len(projects) >= max_projects:
                break
            projects.append(
                {
                    "title": existing_project,
                    "description": (
                        f"An extension or student-contributor opportunity on "
                        f"{name}'s ongoing work: \"{existing_project}\"."
                    ),
                    "related_faculty": name,
                    "faculty_id": faculty_id,
                }
            )

        # If room remains, synthesize ideas by directly combining this
        # faculty's own listed research area with their own listed
        # skill — a grounded pairing, not a fabricated topic.
        if len(projects) < max_projects and research_areas and skills:
            for research_area in research_areas:
                if len(projects) >= max_projects:
                    break
                skill = skills[0]
                projects.append(
                    {
                        "title": f"{research_area} using {skill}",
                        "description": (
                            f"A project applying {name}'s expertise in "
                            f"{skill} to their research area of "
                            f"{research_area}."
                        ),
                        "related_faculty": name,
                        "faculty_id": faculty_id,
                    }
                )

    return projects[:max_projects]


# ---------------------------------------------------------------------------
# 7. Email draft generation
# ---------------------------------------------------------------------------

def generate_email_draft(faculty: Dict[str, Any], purpose: str = "") -> str:
    """
    Generate a professional, concise email draft to a faculty member,
    grounded in their retrieved profile. This function only produces
    text — it never sends anything.

    Args:
        faculty: A single ranked/enriched faculty result dictionary
            (as produced by rank_and_score()).
        purpose: Optional free-text purpose supplied by the student
            (e.g. "requesting mentorship for an NLP project"). If not
            provided, a generic collaboration purpose is used.

    Returns:
        A formatted email draft as a single string, including subject
        line, greeting, body, and closing.
    """
    name = faculty.get("name", "the faculty member")
    institution = faculty.get("institution", "")
    department = faculty.get("department", "")
    extracted = faculty.get("extracted", {})
    research_areas = extracted.get("research_areas", [])

    relevance_line = (
        f"Your work in {', '.join(research_areas)} is closely aligned with "
        f"what I'd like to explore."
        if research_areas
        else (
            "Your research profile in the "
            f"{department} department stood out as a strong match for my "
            "interests."
        )
    )

    purpose_line = (
        purpose.strip()
        if purpose and purpose.strip()
        else "explore a potential research collaboration or mentorship opportunity"
    )

    subject = f"Request to {purpose_line[0].lower() + purpose_line[1:]}" if purpose_line else "Request for Research Collaboration"

    email_lines = [
        f"Subject: {subject}",
        "",
        f"Dear {name},",
        "",
        f"I hope this email finds you well. I am a student interested in "
        f"{purpose_line}.",
        "",
        relevance_line,
        "",
        f"I would be grateful for the opportunity to discuss this further, "
        f"whether through a short meeting or over email, at your "
        f"convenience.",
        "",
        "Thank you very much for your time and consideration.",
        "",
        "Best regards,",
        "[Your Name]",
    ]

    if institution:
        email_lines.insert(6, f"I understand you are affiliated with {institution}.")

    return "\n".join(email_lines)


# ---------------------------------------------------------------------------
# 8. Best-match explanation
# ---------------------------------------------------------------------------

def explain_best_match(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Identify the single best faculty recommendation and explain why it
    outranks the next-best alternative.

    Args:
        results: Ranked results, already scored by rank_and_score().

    Returns:
        A dictionary:
            {
                "best_faculty": Dict[str, Any] or None,
                "reason": str,
                "comparison_with_second_best": str,
            }
        If there are no results, "best_faculty" is None and both
        text fields explain that no match was found.
    """
    if not results:
        return {
            "best_faculty": None,
            "reason": "No faculty matched this query.",
            "comparison_with_second_best": "",
        }

    best = results[0]
    reason = (
        f"'{best.get('name')}' ranked highest with a blended score of "
        f"{best.get('final_score', 0.0):.2f}, combining semantic relevance "
        f"({best.get('score', 0.0):.2f}), keyword overlap "
        f"({best.get('skill_overlap', 0.0):.2f}), and "
        f"{'a department match' if best.get('department_match') else 'no department match'}."
    )

    if len(results) > 1:
        second = results[1]
        comparison = (
            f"'{best.get('name')}' scored {best.get('final_score', 0.0):.2f} "
            f"versus '{second.get('name')}' at "
            f"{second.get('final_score', 0.0):.2f}, primarily due to "
            f"{'stronger keyword overlap' if best.get('skill_overlap', 0) > second.get('skill_overlap', 0) else 'higher overall semantic relevance'}."
        )
    else:
        comparison = "No second-best alternative was available for comparison."

    return {
        "best_faculty": best,
        "reason": reason,
        "comparison_with_second_best": comparison,
    }


# ---------------------------------------------------------------------------
# Orchestration entry point
# ---------------------------------------------------------------------------

def handle_student_query(
    query: str,
    context: RetrieverContext,
    email_purpose: str = "",
) -> Dict[str, Any]:
    """
    End-to-end orchestration: classify intent, retrieve via RAG, rank,
    explain, challenge weak matches, suggest projects, and (if
    relevant) draft an email — returning the strict structured output
    format required by the system.

    Args:
        query: The student's natural-language query.
        context: An initialized RetrieverContext (from
            rag.retriever.initialize_retriever()), created ONCE by the
            caller and reused across queries.
        email_purpose: Optional free-text purpose for an email draft,
            used only when the classified intent is
            "collaboration_request".

    Returns:
        A dictionary with the strict required shape:
            {
                "intent": str,
                "top_matches": List[Dict[str, Any]],
                "warnings": List[str],
                "explanations": List[Dict[str, Any]],
                "projects": List[Dict[str, Any]],
                "best_recommendation": str,
                "email_draft": str,
            }
    """
    intent = classify_intent(query)

    raw_results = retrieve_faculty(query, context=context, top_k=DEFAULT_RETRIEVE_TOP_K)
    ranked_results = rank_and_score(raw_results, query)
    top_matches = ranked_results[:DEFAULT_TOP_MATCHES]

    warnings = devil_advocate_filter(ranked_results, query)
    explanations = generate_explanations(top_matches, query)

    projects: List[Dict[str, Any]] = []
    if intent in ("project_suggestion", "faculty_search") and top_matches:
        projects = suggest_projects(top_matches[:2], max_projects=DEFAULT_PROJECT_COUNT)

    best_match_info = explain_best_match(ranked_results)
    best_recommendation = best_match_info["reason"]

    email_draft = ""
    if intent == "collaboration_request" and top_matches:
        email_draft = generate_email_draft(top_matches[0], purpose=email_purpose)

    return {
        "intent": intent,
        "top_matches": top_matches,
        "warnings": warnings,
        "explanations": explanations,
        "projects": projects,
        "best_recommendation": best_recommendation,
        "email_draft": email_draft,
    }


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from rag.retriever import initialize_retriever

    retriever_context = initialize_retriever()

    if retriever_context is not None:
        sample_query = "I want to work with a faculty member on NLP projects"
        response = handle_student_query(sample_query, context=retriever_context)

        print(f"Intent: {response['intent']}")
        print(f"Best recommendation: {response['best_recommendation']}")
        for warning in response["warnings"]:
            print(warning)
        for project in response["projects"]:
            print(f"- {project['title']} (with {project['related_faculty']})")
>>>>>>> 245bcf6f1d3b7adf0ad9b9f9f243be8bbc264edc
