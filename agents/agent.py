"""
agent.py
========

Main orchestration layer for the Faculty Intelligence &
Research Discovery System.

Responsibilities
----------------
- Initialize the retrieval context
- Select Student / Professor mode
- Delegate work to the appropriate agent
- Display formatted results

This file NEVER:
- Queries ChromaDB directly
- Generates embeddings manually
- Calls the embedding model
"""

from __future__ import annotations

from rag.retriever import initialize_retriever

from agents.student_agent import handle_student_query
from agents.professor_agent import handle_professor_query


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------

def print_header():
    print("\n" + "=" * 60)
    print("AI FACULTY INTELLIGENCE & RESEARCH DISCOVERY SYSTEM")
    print("=" * 60)


def choose_mode():
    print("\nAvailable Modes")
    print("----------------")
    print("1. Student")
    print("2. Professor")

    while True:

        choice = input("\nSelect mode (1/2): ").strip()

        if choice == "1":
            return "student"

        if choice == "2":
            return "professor"

        print("Invalid selection.")


def print_student_output(result):

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)

    print("\nDetected Intent:")
    print(result["intent"])

    print("\nTop Faculty Matches")
    print("-------------------")

    for index, faculty in enumerate(result["top_matches"], start=1):

        print(f"\n{index}. {faculty['name']}")
        print(f"Faculty ID : {faculty['faculty_id']}")
        print(f"Institution: {faculty['institution']}")
        print(f"Department : {faculty['department']}")
        print(f"Designation: {faculty['designation']}")
        print(f"Score      : {faculty['final_score']:.3f}")

    print("\nBest Recommendation")
    print("-------------------")
    print(result["best_recommendation"])

    if result["warnings"]:
        print("\nWarnings")
        print("--------")
        for warning in result["warnings"]:
            print("-", warning)

    if result["projects"]:
        print("\nSuggested Projects")
        print("------------------")

        for project in result["projects"]:

            print(f"\nTitle : {project['title']}")
            print(project["description"])
            print("Faculty :", project["related_faculty"])

    print("\nEmail Draft")
    print("-----------")
    print(result["email_draft"])


# --------------------------------------------------
# Main Controller
# --------------------------------------------------

def start_agent():

    print_header()

    context = initialize_retriever()

    if context is None:

        print("\nUnable to initialize retrieval system.")
        print("Please check ChromaDB and embeddings.")
        return

    mode = choose_mode()

    if mode == "student":

        query = input("\nEnter your research interest:\n> ")

        purpose = input(
            "\nPurpose of contacting faculty (optional):\n> "
        ).strip()

        result = handle_student_query(
            query=query,
            context=context,
            email_purpose=purpose
        )

        print_student_output(result)

    else:

        handle_professor_query(context)


if __name__ == "__main__":
    start_agent()