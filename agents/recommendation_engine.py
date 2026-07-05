"""
recommendation_engine.py
========================

Recommendation Engine

Responsibilities
----------------
- Generate final faculty recommendations.
- Select the best faculty matches.
- Explain why each faculty member is recommended.

This module does NOT:
- Query ChromaDB
- Generate embeddings
- Call Tavily
"""

from agents.student_agent import (
    explain_best_match,
    generate_explanations,
)


def recommend_faculty(ranked_results, top_k=3):
    """
    Return the top faculty recommendations.

    Parameters
    ----------
    ranked_results : list
        Ranked faculty results.

    top_k : int
        Number of recommendations.

    Returns
    -------
    list
    """

    if not ranked_results:
        return []

    return ranked_results[:top_k]


def generate_recommendation_report(ranked_results):
    """
    Generate the final recommendation report.

    Parameters
    ----------
    ranked_results : list

    Returns
    -------
    dict
    """

    if not ranked_results:

        return {
            "best_match": None,
            "recommendations": [],
            "reason": "No suitable faculty found."
        }

    best = explain_best_match(ranked_results)

    explanations = generate_explanations(
        ranked_results,
        ""
    )

    return {

        "best_match":
            best["best_faculty"],

        "reason":
            best["reason"],

        "comparison":
            best["comparison_with_second_best"],

        "recommendations":
            explanations

    }


def print_recommendations(report):
    """
    Pretty print recommendation report.
    """

    print("\nRecommended Faculty")
    print("=" * 60)

    if report["best_match"] is None:

        print("No recommendations found.")
        return

    print("\nBest Match")
    print("----------")

    print(report["best_match"]["name"])

    print(report["reason"])

    print("\nComparison")

    print(report["comparison"])

    print("\nTop Recommendations")
    print("-------------------")

    for faculty in report["recommendations"]:

        print("\nFaculty :", faculty["name"])

        print(
            "Score :",
            round(
                faculty.get(
                    "final_score",
                    faculty.get("score", 0)
                ),
                3
            )
        )

        print(
            "Explanation :",
            faculty.get(
                "explanation",
                "Recommended based on semantic similarity."
            )
        )


if __name__ == "__main__":

    print(
        "Recommendation Engine loaded successfully."
    )
