<<<<<<< HEAD
from sentence_transformers import SentenceTransformer

# load model once
model = SentenceTransformer('all-MiniLM-L6-v2')


# -----------------------------
# TEXT → EMBEDDING
# -----------------------------
def embed_text(text: str):
    """
    Converts text into vector embedding
    """
    return model.encode(text).tolist()


# -----------------------------
# LIST OF PROFILES → EMBEDDINGS
# -----------------------------
def process_profiles(data):

    processed = []

    for item in data:

        text = f"{item['name']} {item['department']} {' '.join(item['research_areas'])}"

        embedding = embed_text(text)

        processed.append({
            "document": text,
            "embedding": embedding,
            "metadata": item
        })

    return processed
=======
"""
embedder.py
===========

Embedding generation module for the AI-powered Faculty Intelligence &
Research Discovery System.

Single Responsibility
----------------------
This module is responsible ONLY for:
    - Converting structured faculty profiles (as produced by
      rag/loader.py) into rich, natural-language documents suitable
      for semantic embedding
    - Extracting lightweight metadata for each profile
    - Generating sentence embeddings for each document
    - Returning the combined (document, embedding, metadata) result
      for every profile

This module explicitly does NOT:
    - Store anything in ChromaDB
    - Perform retrieval or semantic search
    - Call any LLM
    - Perform RAG
    - Call Tavily or any external API
    - Generate emails
    - Contain any chatbot / agent logic

Design principle
-----------------
Sentence embedding models perform far better on coherent natural
language than on raw JSON. Every faculty profile is therefore
rendered into a readable paragraph before being embedded, while a
separate, compact metadata dictionary is kept for filtering/display
purposes (it is NOT embedded and does NOT duplicate the full
document).

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

from rag.loader import load_faculty_profiles


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Name of the sentence-embedding model to use.
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

#: Placeholder used whenever a field is missing, null, or empty.
PLACEHOLDER: str = "Information not available"

#: Module-level cache for the loaded embedding model so it is only
#: loaded once per process and reused across calls.
_model_cache: Optional[SentenceTransformer] = None


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def get_embedding_model() -> SentenceTransformer:
    """
    Load and cache the SentenceTransformer embedding model.

    The model is loaded only once per process. Subsequent calls
    reuse the cached instance instead of reloading it from disk.

    Returns:
        A ready-to-use SentenceTransformer instance.
    """
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model_cache


# ---------------------------------------------------------------------------
# Small field-access helpers (defensive against missing/null/empty data)
# ---------------------------------------------------------------------------

def _safe_get(section: Dict[str, Any], key: str) -> Any:
    """
    Safely fetch a key from a (possibly missing/None) section dict.

    Args:
        section: The dictionary to read from. May be missing or None.
        key: The key to fetch.

    Returns:
        The value at `key`, or None if unavailable.
    """
    if not isinstance(section, dict):
        return None
    return section.get(key)


def _text_or_placeholder(value: Any) -> str:
    """
    Convert a scalar field into display text, substituting a
    placeholder for missing/null/empty values.

    Args:
        value: The raw field value.

    Returns:
        A clean string, never empty.
    """
    if value is None:
        return PLACEHOLDER
    if isinstance(value, str) and not value.strip():
        return PLACEHOLDER
    return str(value).strip()


def _list_or_placeholder(value: Any) -> List[str]:
    """
    Normalize a field expected to be a list of strings.

    Args:
        value: The raw field value (expected to be a list, but may be
            missing, None, a scalar, or contain non-string items).

    Returns:
        A list of non-empty, stripped strings. Empty if nothing usable
        was found.
    """
    if not value:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _join_list(items: List[str], conjunction: str = "and") -> str:
    """
    Join a list of strings into a natural-language, comma-separated
    phrase with a trailing conjunction before the last item.

    Args:
        items: List of strings to join.
        conjunction: Word to place before the final item ("and"/"or").

    Returns:
        A human-readable joined string, or the placeholder if the
        list is empty.
    """
    items = [item for item in items if item]
    if not items:
        return PLACEHOLDER
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return f"{', '.join(items[:-1])}, {conjunction} {items[-1]}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_document(profile: Dict[str, Any]) -> str:
    """
    Convert a single faculty profile into a rich, natural-language
    paragraph optimized for semantic embedding.

    Every meaningful field from the profile is folded into readable
    sentences so that downstream semantic search (e.g. "who works on
    NLP?", "find a Computer Vision collaborator") has the best chance
    of matching relevant faculty. Missing or empty fields are replaced
    with sensible placeholder text rather than causing errors.

    Args:
        profile: A single faculty profile dictionary, as returned by
            rag.loader.load_faculty_profiles().

    Returns:
        A multi-sentence natural-language string describing the
        faculty member.
    """
    identity = profile.get("Identity", {}) or {}
    academic = profile.get("AcademicProfile", {}) or {}
    research_intel = profile.get("ResearchIntelligence", {}) or {}
    research_output = profile.get("ResearchOutput", {}) or {}
    credibility = profile.get("CredibilityLayer", {}) or {}

    name = _text_or_placeholder(_safe_get(identity, "Name"))
    designation = _text_or_placeholder(_safe_get(identity, "Designation"))
    department = _text_or_placeholder(_safe_get(identity, "Department"))
    institution = _text_or_placeholder(_safe_get(identity, "Institution"))

    qualification = _text_or_placeholder(_safe_get(academic, "Qualification"))
    experience = _safe_get(academic, "Experience")
    specializations = _list_or_placeholder(
        _safe_get(academic, "AreasOfSpecialization")
    )

    research_areas = _list_or_placeholder(_safe_get(research_intel, "ResearchAreas"))
    skills = _list_or_placeholder(_safe_get(research_intel, "Skills"))
    expertise_tags = _list_or_placeholder(_safe_get(research_intel, "ExpertiseTags"))

    current_projects = _list_or_placeholder(
        _safe_get(research_output, "CurrentProjects")
    )
    publication_count = _safe_get(research_output, "PublicationCount")
    citation_count = _safe_get(research_output, "CitationCount")

    memberships = _list_or_placeholder(
        _safe_get(credibility, "ProfessionalMemberships")
    )
    awards = _list_or_placeholder(_safe_get(credibility, "AwardsAchievements"))

    sentences: List[str] = []

    # Identity sentence
    sentences.append(
        f"{name} is a {designation} in the {department} department at "
        f"{institution}."
    )

    # Qualification / experience
    if experience is not None and str(experience).strip():
        sentences.append(
            f"{name.split()[0] if name != PLACEHOLDER else 'This faculty member'} "
            f"holds a {qualification} qualification and has "
            f"{_text_or_placeholder(experience)} years of experience."
        )
    else:
        sentences.append(f"Their highest qualification is {qualification}.")

    # Specializations
    sentences.append(
        f"Their specialization includes {_join_list(specializations)}."
    )

    # Research areas
    sentences.append(
        f"Their research interests include {_join_list(research_areas)}."
    )

    # Skills
    sentences.append(f"Their skills include {_join_list(skills)}.")

    # Expertise tags (kept distinct from skills/research areas for recall)
    if expertise_tags:
        sentences.append(
            f"They are recognized for expertise in "
            f"{_join_list(expertise_tags)}."
        )

    # Current projects
    if current_projects:
        sentences.append(
            f"They are currently working on {_join_list(current_projects)}."
        )
    else:
        sentences.append("No current projects are listed at this time.")

    # Publications / citations
    if publication_count or citation_count:
        pub_text = _text_or_placeholder(publication_count)
        cite_text = _text_or_placeholder(citation_count)
        sentences.append(
            f"They have published {pub_text} research papers with "
            f"{cite_text} citations."
        )
    else:
        sentences.append("Publication and citation records are not available.")

    # Memberships / awards
    if memberships:
        sentences.append(f"They are a member of {_join_list(memberships)}.")
    if awards:
        sentences.append(f"Their awards include {_join_list(awards)}.")

    # Contact closing line (kept generic; actual email lives in metadata only)
    sentences.append("Students may contact them through their institutional email.")

    return " ".join(sentences)


def create_metadata(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a compact metadata dictionary for a single faculty
    profile, suitable for storage alongside (but not duplicating) the
    embedded document.

    Args:
        profile: A single faculty profile dictionary.

    Returns:
        A flat dictionary containing identifying and filterable
        metadata fields. Missing values are replaced with a
        placeholder string (for text fields) or 0 (for numeric
        fields) so downstream consumers never encounter None.
    """
    identity = profile.get("Identity", {}) or {}
    research_output = profile.get("ResearchOutput", {}) or {}
    engagement = profile.get("EngagementLayer", {}) or {}
    system_metadata = profile.get("SystemMetadata", {}) or {}

    def _numeric_or_zero(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    return {
        "FacultyID": _text_or_placeholder(_safe_get(identity, "FacultyID")),
        "Name": _text_or_placeholder(_safe_get(identity, "Name")),
        "Institution": _text_or_placeholder(_safe_get(identity, "Institution")),
        "Department": _text_or_placeholder(_safe_get(identity, "Department")),
        "Designation": _text_or_placeholder(_safe_get(identity, "Designation")),
        "PublicationCount": _numeric_or_zero(
            _safe_get(research_output, "PublicationCount")
        ),
        "CitationCount": _numeric_or_zero(
            _safe_get(research_output, "CitationCount")
        ),
        "Email": _text_or_placeholder(_safe_get(engagement, "Email")),
        "MentorshipAvailability": _text_or_placeholder(
            _safe_get(engagement, "MentorshipAvailability")
        ),
        "DataSource": _text_or_placeholder(_safe_get(system_metadata, "DataSource")),
        "LastUpdated": _text_or_placeholder(
            _safe_get(system_metadata, "LastUpdated")
        ),
    }


def generate_embedding(document: str) -> List[float]:
    """
    Generate a semantic embedding vector for a natural-language
    document.

    Args:
        document: The natural-language text to embed (typically the
            output of create_document()).

    Returns:
        A list of floats representing the embedding vector. Returns
        an empty list if the document is empty or embedding fails
        unexpectedly.
    """
    if not document or not document.strip():
        print("[embedder.py] WARNING: Empty document received; skipping embedding.")
        return []

    try:
        model = get_embedding_model()
        vector = model.encode(document, convert_to_numpy=True)
        return vector.tolist()
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[embedder.py] ERROR: Failed to generate embedding: {exc}.")
        return []


def process_profiles(profiles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process a list of faculty profiles end-to-end: build a semantic
    document, generate its embedding, and extract metadata for each
    profile.

    Args:
        profiles: A list of faculty profile dictionaries, typically
            obtained from rag.loader.load_faculty_profiles().

    Returns:
        A list of dictionaries, one per successfully processed
        profile, each with the shape:
            {
                "document": str,
                "embedding": List[float],
                "metadata": Dict[str, Any]
            }
        Profiles that are not dictionaries are skipped with a warning;
        processing continues for the remainder.
    """
    results: List[Dict[str, Any]] = []

    if not profiles:
        print("[embedder.py] WARNING: No profiles supplied to process_profiles().")
        return results

    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            print(
                f"[embedder.py] WARNING: Skipping item at index {index}; "
                f"expected a dict, got {type(profile).__name__}."
            )
            continue

        try:
            document = create_document(profile)
            metadata = create_metadata(profile)
            embedding = generate_embedding(document)

            results.append(
                {
                    "document": document,
                    "embedding": embedding,
                    "metadata": metadata,
                }
            )
        except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
            faculty_id = (
                profile.get("Identity", {}).get("FacultyID")
                if isinstance(profile.get("Identity"), dict)
                else "unknown"
            )
            print(
                f"[embedder.py] ERROR: Failed to process profile "
                f"(FacultyID={faculty_id}): {exc}. Skipping."
            )
            continue

    print(f"[embedder.py] INFO: Processed {len(results)}/{len(profiles)} profile(s).")
    return results


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    loaded_profiles = load_faculty_profiles()
    processed = process_profiles(loaded_profiles)

    if processed:
        print("\n--- Sample processed profile ---")
        print("Document:\n", processed[0]["document"])
        print("\nMetadata:\n", processed[0]["metadata"])
        print("\nEmbedding length:", len(processed[0]["embedding"]))
>>>>>>> 245bcf6f1d3b7adf0ad9b9f9f243be8bbc264edc
