"""
faculty_search.py
=================

Faculty Search Module

Responsibilities
----------------
- Search faculty using semantic search
- Get top faculty matches
- Find faculty by ID

This module does NOT:
- Access ChromaDB directly
- Generate embeddings manually
"""

from rag.retriever import (
    semantic_search,
    faculty_lookup,
)


def search_faculty(query, context, top_k=5):
    """
    Search faculty using semantic search.

    Parameters
    ----------
    query : str
    context : RetrieverContext
    top_k : int

    Returns
    -------
    list
        List of faculty dictionaries.
    """

    try:

        results = semantic_search(
            query=query,
            context=context,
            top_k=top_k
        )

        return results

    except Exception as e:

        print(f"Faculty Search Error: {e}")
        return []


def search_by_faculty_id(faculty_id, context):
    """
    Search exact faculty by FacultyID.
    """

    try:

        return faculty_lookup(
            faculty_id=faculty_id,
            context=context
        )

    except Exception as e:

        print(f"Faculty Lookup Error: {e}")
        return None


def print_search_results(results):
    """
    Pretty print faculty search results.
    """

    if not results:

        print("\nNo faculty found.")
        return

    print("\nTop Faculty Matches")
    print("=" * 60)

    for i, faculty in enumerate(results, start=1):

        print(f"\n{i}. {faculty['name']}")
        print(f"Faculty ID : {faculty['faculty_id']}")
        print(f"Institution: {faculty['institution']}")
        print(f"Department : {faculty['department']}")
        print(f"Designation: {faculty['designation']}")
        print(f"Score      : {faculty['score']:.3f}")


def get_best_match(results):
    """
    Return highest ranked faculty.
    """

    if not results:
        return None

    return results[0]


def get_top_matches(results, n=3):
    """
    Return first n faculty matches.
    """

    return results[:n]


if __name__ == "__main__":

    from rag.retriever import initialize_retriever

    context = initialize_retriever()

    if context is None:

        print("Retriever initialization failed.")

    else:

        query = input("Enter research topic: ")

        results = search_faculty(
            query=query,
            context=context,
            top_k=5
        )

        print_search_results(results)
