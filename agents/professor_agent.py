"""
professor_agent.py
==================

Professor workflow for the AI Faculty Intelligence &
Research Discovery System.
"""

from rag.retriever import semantic_search

from tools.tavily_search import search_trends
from tools.collaboration_engine import find_collaborations
from tools.gap_analyzer import analyze_gaps


def display_matches(results):

    if not results:
        print("\nNo matching faculty found.")
        return

    print("\nMatching Faculty")
    print("-" * 50)

    for faculty in results:

        print(f"\nName        : {faculty['name']}")
        print(f"Institution : {faculty['institution']}")
        print(f"Department  : {faculty['department']}")
        print(f"Score       : {faculty['score']:.3f}")


def handle_professor_query(context):

    print("\n" + "=" * 60)
    print("PROFESSOR MODE")
    print("=" * 60)

    topic = input("\nEnter research topic:\n> ").strip()

    if not topic:
        print("Topic cannot be empty.")
        return

    print("\nSearching faculty database...")

    faculty_results = semantic_search(
        query=topic,
        context=context,
        top_k=10
    )

    display_matches(faculty_results)

    print("\nSearching latest research trends...\n")

    trends = search_trends(topic)

    print(trends)

    collaborations = find_collaborations(faculty_results)

    print("\nPossible Collaborations")
    print("-" * 50)

    if collaborations:

        for item in collaborations:

            print(
                f"{item['faculty_1']}  <-->  "
                f"{item['faculty_2']}"
            )

            print(
                "Shared Areas:",
                ", ".join(item["shared_area"])
            )

            print()

    else:

        print("No collaboration opportunities found.")

    trending_topics = []

    if isinstance(trends, str):

        trending_topics = [
            x.strip()
            for x in trends.split(",")
            if x.strip()
        ]

    gaps = analyze_gaps(
        faculty_results,
        trending_topics
    )

    print("\nResearch Gaps")
    print("-" * 50)

    if gaps:

        for gap in gaps:
            print("-", gap)

    else:

        print("No research gaps detected.")