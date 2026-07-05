"""
gap_analysis.py
===============

Research Gap Analysis

Responsibilities
----------------
- Compare faculty expertise with trending research topics.
- Identify research gaps.

This module does NOT:
- Query ChromaDB
- Call Tavily API
- Generate embeddings
"""

from agents.student_agent import _extract_document_fields


def find_gaps(faculty_results, trending_topics):
    """
    Identify research gaps by comparing faculty expertise
    with trending topics.

    Parameters
    ----------
    faculty_results : list
        Results returned from the RAG retriever.

    trending_topics : list
        Latest research topics from Tavily.

    Returns
    -------
    list
        Topics not currently covered by faculty.
    """

    covered_topics = set()

    for faculty in faculty_results:

        extracted = _extract_document_fields(
            faculty["document"]
        )

        for area in extracted.get("research_areas", []):

            covered_topics.add(area.lower())

    gaps = []

    for topic in trending_topics:

        if topic.lower() not in covered_topics:

            gaps.append(topic)

    return gaps


def print_gap_analysis(gaps):
    """
    Pretty print research gaps.
    """

    print("\nResearch Gap Analysis")
    print("=" * 50)

    if not gaps:

        print("No research gaps found.")
        return

    print("Emerging topics with limited faculty expertise:\n")

    for topic in gaps:

        print("-", topic)


if __name__ == "__main__":

    print(
        "Gap Analysis module should be called "
        "from professor_agent.py"
    )
