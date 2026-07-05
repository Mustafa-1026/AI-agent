"""
collaboration.py
================

Collaboration Engine

Responsibilities
----------------
- Find collaboration opportunities
- Calculate collaboration score
- Identify common research areas

This module does NOT:
- Query ChromaDB
- Generate embeddings
"""

from agents.student_agent import _extract_document_fields


def calculate_collaboration_score(common_areas):
    """
    Calculate collaboration score.

    Parameters
    ----------
    common_areas : list

    Returns
    -------
    float
    """

    if not common_areas:
        return 0.0

    score = min(len(common_areas) * 0.25, 1.0)

    return round(score, 2)


def find_collaboration(faculty_results):
    """
    Find collaboration opportunities among faculty.

    Parameters
    ----------
    faculty_results : list

    Returns
    -------
    list
    """

    collaborations = []

    if len(faculty_results) < 2:
        return collaborations

    for i in range(len(faculty_results)):

        faculty1 = faculty_results[i]

        data1 = _extract_document_fields(
            faculty1["document"]
        )

        research1 = set(data1["research_areas"])

        for j in range(i + 1, len(faculty_results)):

            faculty2 = faculty_results[j]

            data2 = _extract_document_fields(
                faculty2["document"]
            )

            research2 = set(data2["research_areas"])

            common = sorted(
                research1.intersection(research2)
            )

            if common:

                collaborations.append({

                    "faculty_1": faculty1["name"],

                    "faculty_2": faculty2["name"],

                    "faculty_1_id": faculty1["faculty_id"],

                    "faculty_2_id": faculty2["faculty_id"],

                    "shared_area": common,

                    "collaboration_score":
                        calculate_collaboration_score(common)

                })

    collaborations.sort(

        key=lambda x: x["collaboration_score"],

        reverse=True

    )

    return collaborations


def print_collaborations(collaborations):
    """
    Pretty print collaborations.
    """

    if not collaborations:

        print("\nNo collaboration opportunities found.")

        return

    print("\nPossible Collaborations")
    print("=" * 60)

    for item in collaborations:

        print(f"\n{item['faculty_1']}")
        print("        ↕")
        print(item["faculty_2"])

        print(
            "Shared Areas :",
            ", ".join(item["shared_area"])
        )

        print(
            "Synergy Score:",
            item["collaboration_score"]
        )


if __name__ == "__main__":

    print(
        "This module is intended to be called "
        "from professor_agent.py"
    )
