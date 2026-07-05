"""
compatibility.py
================

Compatibility Engine

Responsibilities
----------------
- Calculate compatibility score between
  user query and faculty.
- Explain why a faculty member is a good match.

This module does NOT:
- Query ChromaDB
- Generate embeddings
- Call any external APIs
"""

from agents.student_agent import _extract_document_fields


def calculate_compatibility(faculty, query):
    """
    Calculate compatibility score between
    query and faculty.
    """

    extracted = _extract_document_fields(
        faculty["document"]
    )

    query_words = set(query.lower().split())

    research = {
        area.lower()
        for area in extracted.get("research_areas", [])
    }

    skills = {
        skill.lower()
        for skill in extracted.get("skills", [])
    }

    expertise = {
        tag.lower()
        for tag in extracted.get("expertise_tags", [])
    }

    overlap = (
        query_words & research
    ) | (
        query_words & skills
    ) | (
        query_words & expertise
    )

    semantic_score = faculty.get("score", 0)

    keyword_score = len(overlap) * 0.1

    compatibility = semantic_score + keyword_score

    compatibility = min(compatibility, 1.0)

    return round(compatibility, 3)


def explain_compatibility(faculty, query):
    """
    Explain why a faculty was recommended.
    """

    extracted = _extract_document_fields(
        faculty["document"]
    )

    reasons = []

    query = query.lower()

    for area in extracted.get("research_areas", []):

        if area.lower() in query:

            reasons.append(
                f"Research area match: {area}"
            )

    for skill in extracted.get("skills", []):

        if skill.lower() in query:

            reasons.append(
                f"Skill match: {skill}"
            )

    if not reasons:

        reasons.append(
            "High semantic similarity based on research profile."
        )

    return reasons


def rank_faculty(results, query):
    """
    Rank faculty using compatibility score.
    """

    ranked = []

    for faculty in results:

        faculty["compatibility_score"] = (
            calculate_compatibility(
                faculty,
                query
            )
        )

        faculty["compatibility_reason"] = (
            explain_compatibility(
                faculty,
                query
            )
        )

        ranked.append(faculty)

    ranked.sort(

        key=lambda x: x["compatibility_score"],

        reverse=True

    )

    return ranked


def print_rankings(results):
    """
    Pretty print rankings.
    """

    if not results:

        print("No faculty found.")
        return

    print("\nCompatibility Rankings")
    print("=" * 60)

    for index, faculty in enumerate(results, start=1):

        print(f"\n{index}. {faculty['name']}")

        print(
            "Compatibility:",
            faculty["compatibility_score"]
        )

        print("Reasons:")

        for reason in faculty["compatibility_reason"]:

            print("-", reason)


if __name__ == "__main__":

    print(
        "Compatibility module loaded successfully."
    )
  
