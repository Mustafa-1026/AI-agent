"""
data_loader.py
==============

Loads faculty data and initializes the RAG retriever.

Responsibilities
----------------
- Load faculty profiles
- Initialize retriever context

Does NOT:
- Perform semantic search
- Rank faculty
- Generate recommendations
"""

from rag.loader import load_faculty_profiles
from rag.retriever import initialize_retriever


def load_data():
    """
    Load faculty profiles and initialize the retriever.

    Returns
    -------
    dict
        {
            "profiles": list,
            "context": RetrieverContext
        }
    """

    profiles = load_faculty_profiles()

    context = initialize_retriever()

    return {
        "profiles": profiles,
        "context": context
    }


def get_profiles():
    """
    Return all faculty profiles.
    """

    return load_faculty_profiles()


def get_context():
    """
    Return initialized RetrieverContext.
    """

    return initialize_retriever()


if __name__ == "__main__":

    data = load_data()

    print("Faculty Profiles :", len(data["profiles"]))

    if data["context"]:
        print("Retriever initialized successfully.")
    else:
        print("Retriever initialization failed.")
