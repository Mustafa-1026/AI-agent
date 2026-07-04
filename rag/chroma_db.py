<<<<<<< HEAD
=======
"""
chroma_db.py
============

ChromaDB persistence module for the AI-powered Faculty Intelligence &
Research Discovery System.

Single Responsibility
----------------------
This module is responsible ONLY for:
    - Initializing a persistent ChromaDB client
    - Creating / loading the "faculty_knowledge_base" collection
    - Adding pre-computed documents, embeddings, and metadata into
      that collection
    - Providing basic collection management (count, delete, reset)

This module explicitly does NOT:
    - Perform semantic search or retrieval
    - Answer user questions
    - Call any LLM
    - Call Tavily or any external API
    - Generate embeddings (it only stores embeddings it is given)
    - Load JSON files directly (that is loader.py's job)

Input contract
---------------
This module expects data in the exact shape produced by
rag/embedder.py's `process_profiles()`:

    [
        {
            "document": "...",
            "embedding": [...],
            "metadata": {...}   # must contain a "FacultyID" key
        },
        ...
    ]

Document IDs
------------
Each document is stored under its FacultyID (e.g. "VCE-001",
"IIITH-004") as the ChromaDB entry id. Random UUIDs are never used, so
that faculty records can be reliably upserted/looked up by ID across
runs.

Author: AI Agent Hackathon Team
"""

from __future__ import annotations

>>>>>>> 245bcf6f1d3b7adf0ad9b9f9f243be8bbc264edc
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.client import Client as ChromaClient


<<<<<<< HEAD
# -----------------------------
# CONFIG
# -----------------------------
COLLECTION_NAME = "faculty_knowledge_base"
DEFAULT_PERSIST_DIRECTORY = Path("chroma_store")

_client_cache: Optional[ChromaClient] = None
_collection_cache: Optional[Collection] = None


# -----------------------------
# INIT CLIENT
# -----------------------------
def initialize_client(persist_directory: Optional[Path] = None):

=======
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Name of the ChromaDB collection used for faculty data.
COLLECTION_NAME: str = "faculty_knowledge_base"

#: Directory where ChromaDB will persist its data on disk.
DEFAULT_PERSIST_DIRECTORY: Path = Path("chroma_store")

#: Module-level cache so the client is only initialized once per process.
_client_cache: Optional[ChromaClient] = None

#: Module-level cache so the collection handle is only fetched once.
_collection_cache: Optional[Collection] = None


# ---------------------------------------------------------------------------
# Client / collection lifecycle
# ---------------------------------------------------------------------------

def initialize_client(
    persist_directory: Optional[Path] = None,
) -> ChromaClient:
    """
    Initialize (or return the cached) ChromaDB PersistentClient.

    Using a PersistentClient ensures all stored documents, embeddings,
    and metadata survive program restarts.

    Args:
        persist_directory: Directory on disk where ChromaDB should
            persist its data. Defaults to DEFAULT_PERSIST_DIRECTORY if
            not provided. Ignored if a client has already been
            initialized in this process.

    Returns:
        A chromadb PersistentClient instance.
    """
>>>>>>> 245bcf6f1d3b7adf0ad9b9f9f243be8bbc264edc
    global _client_cache

    if _client_cache is not None:
        return _client_cache

<<<<<<< HEAD
    directory = persist_directory or DEFAULT_PERSIST_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)

    _client_cache = chromadb.PersistentClient(path=str(directory))

    return _client_cache


# -----------------------------
# CREATE / GET COLLECTION
# -----------------------------
def create_collection(client=None):

    global _collection_cache

    client = client or initialize_client()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Faculty knowledge base"},
    )

    _collection_cache = collection
    return collection


def get_collection(client=None):

    global _collection_cache

    if _collection_cache is not None:
        return _collection_cache

    return create_collection(client)


# -----------------------------
# ADD DATA TO CHROMA
# -----------------------------
def add_faculty_documents(processed_profiles, collection=None):

    collection = collection or get_collection()

    ids = []
    documents = []
    embeddings = []
    metadatas = []

    for item in processed_profiles:

        ids.append(item["metadata"]["FacultyID"])
        documents.append(item["document"])
        embeddings.append(item["embedding"])
        metadatas.append(item["metadata"])

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    return len(ids)


# -----------------------------
# COUNT
# -----------------------------
def count_documents(collection=None):

    collection = collection or get_collection()

    return collection.count()
=======
    directory = Path(persist_directory) if persist_directory else DEFAULT_PERSIST_DIRECTORY

    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(
            f"[chroma_db.py] ERROR: Could not create persist directory "
            f"'{directory}': {exc}."
        )
        raise

    print("Initializing ChromaDB...")
    try:
        _client_cache = chromadb.PersistentClient(path=str(directory))
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[chroma_db.py] ERROR: Failed to initialize ChromaDB client: {exc}.")
        raise

    print(f"ChromaDB client initialized at '{directory}'.")
    return _client_cache


def create_collection(
    client: Optional[ChromaClient] = None,
) -> Collection:
    """
    Create the faculty knowledge base collection if it does not
    already exist, or load it if it does.

    Args:
        client: An initialized ChromaDB client. If not provided,
            initialize_client() is called to obtain one.

    Returns:
        The ChromaDB Collection object for "faculty_knowledge_base".
    """
    global _collection_cache

    active_client = client if client is not None else initialize_client()

    try:
        collection = active_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Faculty Intelligence & Research Discovery knowledge base"},
        )
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[chroma_db.py] ERROR: Failed to create/load collection: {exc}.")
        raise

    _collection_cache = collection
    print("Collection loaded.")
    return collection


def get_collection(
    client: Optional[ChromaClient] = None,
) -> Collection:
    """
    Return the active faculty knowledge base collection, creating or
    loading it if it has not been fetched yet in this process.

    Args:
        client: An initialized ChromaDB client. Only used if the
            collection has not already been cached.

    Returns:
        The ChromaDB Collection object for "faculty_knowledge_base".
    """
    if _collection_cache is not None:
        return _collection_cache
    return create_collection(client=client)


# ---------------------------------------------------------------------------
# Data validation helpers
# ---------------------------------------------------------------------------

def _validate_entry(entry: Dict[str, Any], index: int) -> Optional[str]:
    """
    Validate a single processed-profile entry before insertion.

    Args:
        entry: One item from the processed_profiles list, expected to
            contain "document", "embedding", and "metadata".
        index: Position of the entry in the input list, used for
            clearer log messages.

    Returns:
        The FacultyID to use as the document id if the entry is valid,
        otherwise None (in which case the entry should be skipped).
    """
    if not isinstance(entry, dict):
        print(
            f"[chroma_db.py] WARNING: Skipping entry at index {index}; "
            f"expected a dict, got {type(entry).__name__}."
        )
        return None

    document = entry.get("document")
    embedding = entry.get("embedding")
    metadata = entry.get("metadata")

    if not document or not isinstance(document, str) or not document.strip():
        print(
            f"[chroma_db.py] WARNING: Skipping entry at index {index}; "
            f"invalid or empty 'document'."
        )
        return None

    if not embedding or not isinstance(embedding, list):
        print(
            f"[chroma_db.py] WARNING: Skipping entry at index {index}; "
            f"missing or invalid 'embedding'."
        )
        return None

    if not metadata or not isinstance(metadata, dict):
        print(
            f"[chroma_db.py] WARNING: Skipping entry at index {index}; "
            f"missing or invalid 'metadata'."
        )
        return None

    faculty_id = metadata.get("FacultyID")
    if not faculty_id or not isinstance(faculty_id, str) or not faculty_id.strip():
        print(
            f"[chroma_db.py] WARNING: Skipping entry at index {index}; "
            f"metadata is missing a valid 'FacultyID'."
        )
        return None

    return faculty_id.strip()


# ---------------------------------------------------------------------------
# Public API — data ingestion
# ---------------------------------------------------------------------------

def add_faculty_documents(
    processed_profiles: List[Dict[str, Any]],
    collection: Optional[Collection] = None,
) -> int:
    """
    Add a list of processed faculty profiles (documents, embeddings,
    metadata) into the faculty knowledge base collection.

    Each entry is stored using its FacultyID (from metadata) as the
    ChromaDB entry id. If a FacultyID already exists in the
    collection, it is upserted (updated) rather than duplicated.

    Args:
        processed_profiles: A list of dicts as produced by
            embedder.process_profiles(), each shaped as:
                {"document": str, "embedding": List[float], "metadata": dict}
        collection: An existing ChromaDB collection to add to. If not
            provided, get_collection() is used.

    Returns:
        The number of documents successfully added/updated. Invalid
        entries are skipped with a warning rather than raising.
    """
    if not processed_profiles:
        print("[chroma_db.py] WARNING: No processed profiles supplied; nothing to add.")
        return 0

    active_collection = collection if collection is not None else get_collection()

    ids: List[str] = []
    documents: List[str] = []
    embeddings: List[List[float]] = []
    metadatas: List[Dict[str, Any]] = []

    seen_ids: set = set()

    print(f"Adding {len(processed_profiles)} faculty profiles...")

    for index, entry in enumerate(processed_profiles):
        faculty_id = _validate_entry(entry, index)
        if faculty_id is None:
            continue

        if faculty_id in seen_ids:
            print(
                f"[chroma_db.py] WARNING: Duplicate FacultyID '{faculty_id}' "
                f"within this batch; keeping the last occurrence."
            )

        seen_ids.add(faculty_id)
        ids.append(faculty_id)
        documents.append(entry["document"])
        embeddings.append(entry["embedding"])
        metadatas.append(entry["metadata"])

    if not ids:
        print("[chroma_db.py] WARNING: No valid entries to add after validation.")
        return 0

    try:
        active_collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[chroma_db.py] ERROR: Failed to add documents to ChromaDB: {exc}.")
        return 0

    print(f"{len(ids)} documents stored successfully.")
    print("Collection ready.")
    return len(ids)


# ---------------------------------------------------------------------------
# Public API — collection management
# ---------------------------------------------------------------------------

def count_documents(collection: Optional[Collection] = None) -> int:
    """
    Return the number of faculty documents currently stored in the
    collection.

    Args:
        collection: An existing ChromaDB collection. If not provided,
            get_collection() is used.

    Returns:
        The document count, or 0 if the count could not be retrieved.
    """
    active_collection = collection if collection is not None else get_collection()

    try:
        return active_collection.count()
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(f"[chroma_db.py] ERROR: Failed to count documents: {exc}.")
        return 0


def delete_collection(client: Optional[ChromaClient] = None) -> bool:
    """
    Delete the faculty knowledge base collection entirely.

    Args:
        client: An initialized ChromaDB client. If not provided,
            initialize_client() is called to obtain one.

    Returns:
        True if the collection was deleted successfully (or did not
        exist), False if deletion failed unexpectedly.
    """
    global _collection_cache

    active_client = client if client is not None else initialize_client()

    try:
        active_client.delete_collection(name=COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' deleted.")
    except Exception as exc:  # noqa: BLE001 - defensive catch-all by design
        print(
            f"[chroma_db.py] WARNING: Could not delete collection "
            f"'{COLLECTION_NAME}' (it may not exist): {exc}."
        )
        _collection_cache = None
        return False

    _collection_cache = None
    return True


def reset_database(client: Optional[ChromaClient] = None) -> Collection:
    """
    Delete and recreate the faculty knowledge base collection from
    scratch. Useful during development/testing to clear out stale
    data.

    Args:
        client: An initialized ChromaDB client. If not provided,
            initialize_client() is called to obtain one.

    Returns:
        The freshly created, empty Collection object.
    """
    active_client = client if client is not None else initialize_client()

    print(f"Resetting database: deleting collection '{COLLECTION_NAME}' if present...")
    delete_collection(client=active_client)

    print("Recreating collection...")
    return create_collection(client=active_client)


# ---------------------------------------------------------------------------
# Manual/standalone execution (useful for quick sanity checks during dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    db_client = initialize_client()
    faculty_collection = create_collection(client=db_client)
    print(f"Current document count: {count_documents(faculty_collection)}")
>>>>>>> 245bcf6f1d3b7adf0ad9b9f9f243be8bbc264edc
