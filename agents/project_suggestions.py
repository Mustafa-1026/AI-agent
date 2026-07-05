"""
project_suggestions.py
======================

Faculty-Aware Project Suggestion Engine

Responsibilities
----------------
- Generate project ideas based on the
  faculty's expertise and current projects.

This module does NOT:
- Query ChromaDB
- Generate embeddings
- Call Tavily
"""

from agents.student_agent import _extract_document_fields


def suggest_projects(faculty_results, max_projects=3):
    """
    Generate project suggestions.

    Parameters
    ----------
    faculty_results : list
        Ranked faculty results.

    max_projects : int
        Maximum number of projects to return.

    Returns
    -------
    list
    """

    suggestions = []

    for faculty in faculty_results:

        extracted = _extract_document_fields(
            faculty["document"]
        )

        research_areas = extracted.get(
            "research_areas",
            []
        )

        current_projects = extracted.get(
            "current_projects",
            []
        )

        # Suggest based on current projects
        if current_projects:

            for project in current_projects:

                suggestions.append({

                    "title": project,

                    "description":
                        f"Extend or improve '{project}' using recent AI techniques.",

                    "related_faculty":
                        faculty["name"],

                    "faculty_id":
                        faculty["faculty_id"]

                })

        # Suggest based on research areas
        else:

            for area in research_areas:

                suggestions.append({

                    "title":
                        f"{area} Research Project",

                    "description":
                        f"Develop an innovative project in {area}.",

                    "related_faculty":
                        faculty["name"],

                    "faculty_id":
                        faculty["faculty_id"]

                })

    return suggestions[:max_projects]


def print_projects(projects):
    """
    Display project suggestions.
    """

    print("\nProject Suggestions")
    print("=" * 60)

    if not projects:

        print("No projects available.")
        return

    for i, project in enumerate(projects, start=1):

        print(f"\n{i}. {project['title']}")

        print(
            "Faculty :",
            project["related_faculty"]
        )

        print(
            "Description :",
            project["description"]
        )


if __name__ == "__main__":

    print(
        "Project Suggestion module "
        "should be called from student_agent.py"
    )
