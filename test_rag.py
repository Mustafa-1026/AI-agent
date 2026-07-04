from rag.loader import load_faculty_profiles
from rag.embedder import process_profiles
from rag.chroma_db import (
    initialize_client,
    create_collection,
    add_faculty_documents,
)
from rag.retriever import initialize_retriever, semantic_search


def build_database():
    print("\n🚀 STEP 1: Loading faculty profiles...")

    profiles = load_faculty_profiles()
    print(f"Loaded {len(profiles)} faculty profiles")

    print("\n🧠 STEP 2: Generating embeddings...")
    processed_profiles = process_profiles(profiles)

    print("\n🗄️ STEP 3: Initializing ChromaDB...")
    initialize_client()
    create_collection()

    print("\n📦 STEP 4: Storing embeddings in ChromaDB...")
    add_faculty_documents(processed_profiles)

    print("\n✅ DATABASE READY!\n")


def run_tests():
    test_queries = [
        "Who works on NLP?",
        "Machine Learning experts",
        "Computer Vision faculty",
        "Explainable AI researchers",
        "Cybersecurity experts",
        "Who knows TensorFlow?",
        "Data Science professors",
        "AI research in this college",
        "Deep Learning specialists",
        "Healthcare AI researchers",
    ]

    print("\n==============================")
    print("🔎 TESTING RAG RETRIEVAL")
    print("==============================")

    # Build the retriever context ONCE — loads the model + collection
    context = initialize_retriever()
    if context is None:
        print("❌ Failed to initialize retriever. Aborting tests.")
        return

    for query in test_queries:
        print(f"\n\n🧾 QUERY: {query}")

        results = semantic_search(query, context=context)

        if not results:
            print("❌ No results found")
            continue

        for i, r in enumerate(results):
            print(f"\n{i+1}. {r['name']} ({r['score']:.2f})")
            print(f"   📘 Department: {r['department']}")
            print(f"   🆔 Faculty ID: {r['faculty_id']}")
            print(f"   🏫 Institution: {r['institution']}")


if __name__ == "__main__":
    build_database()
    run_tests()