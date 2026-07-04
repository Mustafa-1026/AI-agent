"""
retriever.py
============

Semantic retrieval engine for the AI-powered Faculty Intelligence &
Research Discovery System.

Single Responsibility
----------------------
This module is responsible ONLY for:
    - Loading the existing, already-populated ChromaDB collection
      (never recreating it or regenerating embeddings)
    - Embedding user queries with the same SentenceTransformer model
      used by embedder.py
    - Running semantic similarity search, exact FacultyID lookup,
      department lookup, institution lookup, and combined
      (semantic + metadata) search
    - Returning complete, structured retrieval results so that
      downstream agents never need to touch ChromaDB directly

This module explicitly does NOT:
    - Call any LLM
    - Answer questions in natural language
    - Call Tavily or any external API
    - Generate emails
    - Perform agent reasoning, recommendations, or ranking logic
      beyond similarity scoring
    - Implement Student Mode / Professor Mode
    - Perform collaboration-matching logic

Design note on state
---------------------
Per the "no global mutable state" requirement, this module does not
rely on module-level singletons. Instead, `initialize_retriever()`
returns a `RetrieverContext` object that bundles the loaded embedding
model and ChromaDB collection. Callers pass that context into every
other function, so the "load once, reuse everywhere" performance goal
is met without hidden global state.

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer
from chromadb.api.models.Collection import Collection

from rag.chroma_db import get_collection

# NOTE: chroma_db.py already imports/depends on chromadb; retriever.py
# only needs the Collection type and the get_collection() accessor —
# it never creates, resets, or deletes the collection itself.


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Name of the sentence-embedding model. MUST match embedder.py exactly,
#: since queries and stored documents must live in the same vector space.
EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

#: Default number of results returned by semantic search.
DEFAULT_TOP_K: int = 5


# ---------------------------------------------------------------------------
# Context object (replaces module-level globals)
# ---------------------------------------------------------------------------

@dataclass
class RetrieverContext:
    """
    Bundles the resources a retrieval operation needs so they can be
    loaded once and reused, without relying on module-level mutable
    state.

    Attributes:
        model: The loaded SentenceTransformer embedding model.
        collection: The loaded ChromaDB collection handle
            ("faculty_knowledge_base").
    """

    model: SentenceTransformer
    collection: Collection


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

def initialize_retriever() -> Optional[RetrieverContext]:
    """
    Initialize the retrieval engine: load the embedding model once and
    load (never recreate) the existing ChromaDB faculty collection.

    Returns:
        A RetrieverContext bundling the model and collection, or None
        if initialization failed (e.g. the collection does not exist
        yet or ChromaDB could not be reached). Callers should check
        for None before using the context.
    """
    try:
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[retriever.py] ERROR: Failed to load embedding model: {exc}.")
        return None

    try:
        collection = get_collection()
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[retriever.py] ERROR: Failed to load ChromaDB collection: {exc}.")
        return None

    print("Retriever initialized.")
    return RetrieverContext(model=model, collection=collection)


# ---------------------------------------------------------------------------
# Query embedding
# ---------------------------------------------------------------------------

def generate_query_embedding(
    query: str,
    context: RetrieverContext,
) -> Optional[List[float]]:
    """
    Generate a semantic embedding vector for a user query, using the
    same embedding model that produced the stored faculty embeddings.

    Args:
        query: The raw user query text.
        context: An initialized RetrieverContext.

    Returns:
        The embedding vector as a list of floats, or None if the
        query is empty/invalid or embedding fails.
    """
    if not query or not query.strip():
        print("[retriever.py] WARNING: Empty query received; cannot embed.")
        return None

    print("Embedding query...")
    try:
        vector = context.model.encode(query.strip(), convert_to_numpy=True)
        return vector.tolist()
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[retriever.py] ERROR: Failed to embed query: {exc}.")
        return None


# ---------------------------------------------------------------------------
# Result formatting helpers
# ---------------------------------------------------------------------------

def _distance_to_similarity(distance: Optional[float]) -> float:
    """
    Convert a ChromaDB distance value into a normalized similarity
    score in the approximate range (0, 1], where higher means more
    similar.

    This normalization is metric-agnostic (works reasonably for both
    L2 and cosine distance spaces) and is intended purely for ranking
    and display purposes (e.g. match percentage), not as an absolute
    probability.

    Args:
        distance: The raw distance returned by ChromaDB. May be None
            if unavailable.

    Returns:
        A float similarity score. Returns 0.0 if distance is missing
        or invalid.
    """
    if distance is None:
        return 0.0
    try:
        distance_value = float(distance)
    except (TypeError, ValueError):
        return 0.0
    if distance_value < 0:
        distance_value = 0.0
    return 1.0 / (1.0 + distance_value)


def _build_result(
    document: Optional[str],
    metadata: Optional[Dict[str, Any]],
    score: float,
) -> Dict[str, Any]:
    """
    Assemble a single structured retrieval result from raw ChromaDB
    pieces, filling in placeholders for anything missing so agents
    downstream never encounter None where a string is expected.

    Args:
        document: The stored natural-language document text.
        metadata: The stored metadata dictionary for this faculty
            member.
        score: The similarity score already computed for this result.

    Returns:
        A dictionary with keys: faculty_id, name, institution,
        department, designation, score, document, metadata.
    """
    safe_metadata = metadata if isinstance(metadata, dict) else {}

    return {
        "faculty_id": safe_metadata.get("FacultyID", "Unknown"),
        "name": safe_metadata.get("Name", "Unknown"),
        "institution": safe_metadata.get("Institution", "Unknown"),
        "department": safe_metadata.get("Department", "Unknown"),
        "designation": safe_metadata.get("Designation", "Unknown"),
        "score": round(score, 4),
        "document": document or "",
        "metadata": safe_metadata,
    }


# ---------------------------------------------------------------------------
# Public API — search functions
# ---------------------------------------------------------------------------

def semantic_search(
    query: str,
    context: RetrieverContext,
    top_k: int = DEFAULT_TOP_K,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Perform a pure semantic similarity search against the faculty
    knowledge base.

    Args:
        query: Natural-language query, e.g. "Who works on NLP?" or
            "Find Computer Vision experts".
        context: An initialized RetrieverContext.
        top_k: Maximum number of results to return. Defaults to
            DEFAULT_TOP_K (5).
        where: Optional ChromaDB metadata filter (e.g.
            {"Department": "Computer Science"}) applied alongside the
            semantic search. Used internally by combined_search().

    Returns:
        A list of structured result dictionaries (see _build_result),
        ordered from most to least similar. Returns an empty list on
        any failure or if there are no results.
    """
    if context is None or context.collection is None:
        print("[retriever.py] ERROR: Retriever context/collection is missing.")
        return []

    if top_k <= 0:
        print("[retriever.py] WARNING: top_k must be positive; defaulting to 1.")
        top_k = 1

    query_embedding = generate_query_embedding(query, context)
    if query_embedding is None:
        return []

    print("Searching ChromaDB...")
    try:
        query_kwargs: Dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            query_kwargs["where"] = where

        raw_results = context.collection.query(**query_kwargs)
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[retriever.py] ERROR: ChromaDB query failed: {exc}.")
        return []

    documents = (raw_results.get("documents") or [[]])[0]
    metadatas = (raw_results.get("metadatas") or [[]])[0]
    distances = (raw_results.get("distances") or [[]])[0]

    if not documents:
        print("[retriever.py] INFO: No search results found.")
        return []

    results: List[Dict[str, Any]] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        score = _distance_to_similarity(distance)
        results.append(_build_result(document, metadata, score))

    print(f"Top {len(results)} results returned.")
    return results


def faculty_lookup(
    faculty_id: str,
    context: RetrieverContext,
) -> Optional[Dict[str, Any]]:
    """
    Perform an exact lookup of a single faculty member by FacultyID.

    Args:
        faculty_id: The exact FacultyID to search for (e.g. "VCE-001").
        context: An initialized RetrieverContext.

    Returns:
        A structured result dictionary with a score of 1.0 (exact
        match), or None if not found or on error.
    """
    if context is None or context.collection is None:
        print("[retriever.py] ERROR: Retriever context/collection is missing.")
        return None

    if not faculty_id or not faculty_id.strip():
        print("[retriever.py] WARNING: Empty faculty_id supplied to faculty_lookup().")
        return None

    try:
        raw_results = context.collection.get(
            where={"FacultyID": faculty_id.strip()},
            include=["documents", "metadatas"],
        )
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[retriever.py] ERROR: ChromaDB get() failed: {exc}.")
        return None

    documents = raw_results.get("documents") or []
    metadatas = raw_results.get("metadatas") or []

    if not documents:
        print(f"[retriever.py] INFO: No faculty found with FacultyID '{faculty_id}'.")
        return None

    return _build_result(documents[0], metadatas[0], score=1.0)


def department_lookup(
    department: str,
    context: RetrieverContext,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all faculty members belonging to a given department.

    Args:
        department: Department name to filter by (e.g.
            "Computer Science and Engineering"). Matching is exact
            against the stored metadata value.
        context: An initialized RetrieverContext.
        top_k: Optional cap on the number of results returned. If
            None, all matches are returned.

    Returns:
        A list of structured result dictionaries with a score of 1.0
        (metadata match, not similarity-ranked). Empty list if none
        found or on error.
    """
    return _metadata_lookup(
        field="Department",
        value=department,
        context=context,
        top_k=top_k,
        empty_warning="Empty department supplied to department_lookup().",
    )


def institution_lookup(
    institution: str,
    context: RetrieverContext,
    top_k: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all faculty members belonging to a given institution.

    Args:
        institution: Institution name to filter by (e.g.
            "Vardhaman College of Engineering"). Matching is exact
            against the stored metadata value.
        context: An initialized RetrieverContext.
        top_k: Optional cap on the number of results returned. If
            None, all matches are returned.

    Returns:
        A list of structured result dictionaries with a score of 1.0
        (metadata match, not similarity-ranked). Empty list if none
        found or on error.
    """
    return _metadata_lookup(
        field="Institution",
        value=institution,
        context=context,
        top_k=top_k,
        empty_warning="Empty institution supplied to institution_lookup().",
    )


def _metadata_lookup(
    field: str,
    value: str,
    context: RetrieverContext,
    top_k: Optional[int],
    empty_warning: str,
) -> List[Dict[str, Any]]:
    """
    Shared implementation for exact metadata-field lookups (used by
    department_lookup and institution_lookup) to avoid duplicated
    logic.

    Args:
        field: The metadata field name to filter on (e.g.
            "Department" or "Institution").
        value: The value to match exactly.
        context: An initialized RetrieverContext.
        top_k: Optional cap on the number of results returned.
        empty_warning: Warning message to print if `value` is empty.

    Returns:
        A list of structured result dictionaries, capped at top_k if
        provided.
    """
    if context is None or context.collection is None:
        print("[retriever.py] ERROR: Retriever context/collection is missing.")
        return []

    if not value or not value.strip():
        print(f"[retriever.py] WARNING: {empty_warning}")
        return []

    try:
        raw_results = context.collection.get(
            where={field: value.strip()},
            include=["documents", "metadatas"],
        )
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[retriever.py] ERROR: ChromaDB get() failed for {field}: {exc}.")
        return []

    documents = raw_results.get("documents") or []
    metadatas = raw_results.get("metadatas") or []

    if not documents:
        print(f"[retriever.py] INFO: No faculty found with {field}='{value}'.")
        return []

    results = [
        _build_result(document, metadata, score=1.0)
        for document, metadata in zip(documents, metadatas)
    ]

    if top_k is not None and top_k > 0:
        results = results[:top_k]

    return results


def combined_search(
    query: str,
    context: RetrieverContext,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = DEFAULT_TOP_K,
) -> List[Dict[str, Any]]:
    """
    Perform a semantic search combined with exact metadata filtering.

    Example: "Show Computer Vision faculty from IIIT Hyderabad" would
    be handled by passing the semantic query text (e.g. "Computer
    Vision") alongside filters={"Institution": "IIIT Hyderabad"}.

    Args:
        query: Natural-language semantic query text.
        context: An initialized RetrieverContext.
        filters: Optional dictionary of exact metadata filters, e.g.
            {"Department": "Computer Science", "Institution": "IIIT Hyderabad"}.
            If it contains more than one key, they are combined with a
            logical AND for ChromaDB's `where` clause.
        top_k: Maximum number of results to return.

    Returns:
        A list of structured result dictionaries ranked by similarity
        score, restricted to entries matching all provided filters.
        Empty list on failure or no matches.
    """
    where_clause: Optional[Dict[str, Any]] = None

    if filters:
        clean_filters = {
            key: value
            for key, value in filters.items()
            if value is not None and str(value).strip()
        }
        if clean_filters:
            if len(clean_filters) == 1:
                where_clause = clean_filters
            else:
                where_clause = {
                    "$and": [{key: value} for key, value in clean_filters.items()]
                }

    return semantic_search(query=query, context=context, top_k=top_k, where=where_clause)


def get_top_matches(
    query: str,
    context: RetrieverContext,
    top_k: int = DEFAULT_TOP_K,
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper returning the top-K ranked semantic matches
    for a query, sorted from highest to lowest similarity score.

    This exists as a thin, explicitly-named entry point for agents
    that specifically want "the best N matches" without needing to
    know about metadata filtering.

    Args:
        query: Natural-language query text.
        context: An initialized RetrieverContext.
        top_k: Number of top matches to return. Defaults to
            DEFAULT_TOP_K (5).

    Returns:
        A list of structured result dictionaries, already sorted by
        descending similarity score (ChromaDB returns results in this
        order, but the sort is reasserted here defensively).
    """
    results = semantic_search(query=query, context=context, top_k=top_k)
    return sorted(results, key=lambda item: item["score"], reverse=True)


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    retriever_context = initialize_retriever()

    if retriever_context is not None:
        sample_results = get_top_matches(
            "Who works on Explainable AI and Machine Learning?",
            context=retriever_context,
            top_k=3,
        )
        for rank, result in enumerate(sample_results, start=1):
            print(
                f"{rank}. {result['name']} ({result['faculty_id']}) — "
                f"score={result['score']}"
            )