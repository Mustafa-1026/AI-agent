"""
main.py
=======

CLI entry point for the AI Academic Intelligence System.

This file ONLY calls into the existing backend:
    - rag/retriever.py      (initialize_retriever)
    - agents/student_agent.py   (handle_student_query)
    - agents/professor_agent.py (handle_professor_query)

It does not reimplement embeddings, ChromaDB search, or any
ranking/NLP logic — all of that lives in the modules above.
"""

from __future__ import annotations

import sys
from typing import Any, Dict

from rag.retriever import initialize_retriever, RetrieverContext
from agents.student_agent import handle_student_query
from agents.professor_agent import (
    handle_professor_query,
    explain_collaboration_recommendation,
)


def print_header() -> None:
    print("\n" + "=" * 60)
    print("AI ACADEMIC INTELLIGENCE SYSTEM")
    print("=" * 60)


def choose_mode() -> str:
    while True:
        choice = input("\nChoose mode (student/professor/exit): ").strip().lower()
        if choice in ("student", "professor", "exit", "quit"):
            return choice
        print("Invalid choice. Please type 'student', 'professor', or 'exit'.")


def run_student_mode(context: RetrieverContext) -> None:
    query = input("\nEnter your academic query: ").strip()
    if not query:
        print("Empty query — skipping.")
        return

    try:
        result: Dict[str, Any] = handle_student_query(query, context=context)
    except Exception as exc:  # noqa: BLE001 - never crash the CLI loop
        print(f"\n[main.py] ERROR: Failed to process query: {exc}")
        return

    top_matches = result.get("top_matches", [])
    warnings = result.get("warnings", [])
    projects = result.get("projects", [])
    best_recommendation = result.get("best_recommendation", "")

    print(f"\nIntent detected: {result.get('intent', 'unknown')}")

    if warnings:
        print("\n⚠ WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")

    print("\n🏆 TOP MATCHES:")
    if not top_matches:
        print("  No matching faculty found.")
    else:
        for i, faculty in enumerate(top_matches, 1):
            score = faculty.get("final_score", faculty.get("score", 0.0))
            print(f"\n  {i}. {faculty.get('name', 'Unknown')}")
            print(f"     Department:  {faculty.get('department', 'Unknown')}")
            print(f"     Institution: {faculty.get('institution', 'Unknown')}")
            print(f"     Score:       {score:.2f}")

    if best_recommendation:
        print(f"\n✅ Best recommendation: {best_recommendation}")

    if projects:
        print("\n💡 PROJECT SUGGESTIONS:")
        for project in projects:
            print(f"  - {project.get('title', 'Untitled')}")
            print(f"    {project.get('description', '')}")


def run_professor_mode(context: RetrieverContext) -> None:
    query = input("\nEnter your research-strategy query: ").strip()
    if not query:
        print("Empty query — skipping.")
        return

    sender_name = input("Your name (for email drafts, optional): ").strip()

    try:
        result: Dict[str, Any] = handle_professor_query(
            query, context=context, sender_name=sender_name
        )
    except Exception as exc:  # noqa: BLE001 - never crash the CLI loop
        print(f"\n[main.py] ERROR: Failed to process query: {exc}")
        return

    candidates = result.get("candidates", [])
    collaboration_matches = result.get("collaboration_matches", [])
    research_trends = result.get("research_trends", {})
    research_gaps = result.get("research_gaps", [])
    warnings = result.get("warnings", [])
    project_suggestions = result.get("project_suggestions", [])

    print(f"\nIntent detected: {result.get('intent', 'unknown')}")

    if warnings:
        print("\n⚠ WARNINGS:")
        for warning in warnings:
            print(f"  {warning}")

    print("\n🌐 FACULTY CANDIDATES:")
    if not candidates:
        print("  No faculty candidates found.")
    else:
        for i, faculty in enumerate(candidates, 1):
            score = faculty.get("final_score", faculty.get("score", 0.0))
            print(
                f"  {i}. {faculty.get('name', 'Unknown')} "
                f"({faculty.get('institution', 'Unknown')}) — score {score:.2f}"
            )

    print("\n📈 RESEARCH TRENDS:")
    if research_trends.get("available"):
        print(f"  {research_trends.get('raw_summary', '')}")
    else:
        print("  External trend search unavailable — using internal dataset only.")

    if research_gaps:
        print("\n🔍 RESEARCH GAPS:")
        for gap in research_gaps:
            print(f"  - {gap}")

    if collaboration_matches:
        print("\n🤝 COLLABORATION SUGGESTIONS:")
        for pair in collaboration_matches:
            print(f"  {explain_collaboration_recommendation(pair)}")

    if project_suggestions:
        print("\n💡 JOINT PROJECT SUGGESTIONS:")
        for project in project_suggestions:
            print(f"  - {project.get('title', 'Untitled')}")
            print(f"    {project.get('description', '')}")


def main() -> None:
    print_header()

    print("\nInitializing system...")
    context = initialize_retriever()

    if context is None:
        print(
            "\n[main.py] ERROR: Could not initialize the retriever. "
            "Make sure the ChromaDB collection has been built "
            "(run your database build script first)."
        )
        sys.exit(1)

    print("System ready.\n")

    while True:
        mode = choose_mode()

        if mode in ("exit", "quit"):
            print("\nGoodbye!")
            break
        elif mode == "student":
            run_student_mode(context)
        elif mode == "professor":
            run_professor_mode(context)


if __name__ == "__main__":
    main()