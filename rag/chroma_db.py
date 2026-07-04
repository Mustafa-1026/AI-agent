from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.client import Client as ChromaClient


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

    global _client_cache

    if _client_cache is not None:
        return _client_cache

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