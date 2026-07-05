from rag.chroma_db import get_collection
from rag.embedder import embed_text
from rag.retriever import retrieve_faculty
from agents.recommendation_engine import recommend_faculty

from agents.student_agent import show_best_match, tell_about_faculty
from agents.professor_agent import professor_mode


# -----------------------------
# EXPLAINABILITY ENGINE
# -----------------------------
def explain_match(query, faculty):
    reasons = []

    query = query.lower()

    for area in faculty.get("research_areas", []):
        if area.lower() in query:
            reasons.append(f"Matches research area: {area}")

    if not reasons:
        reasons.append("Semantic similarity from research profile")

    return reasons


# -----------------------------
# FORMAT CHROMA RESULTS
# -----------------------------
def format_results(results):

    formatted = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for i in range(len(documents)):

        formatted.append({
            "name": metadatas[i].get("name", "Unknown"),
            "department": metadatas[i].get("department", "Unknown"),
            "research_areas": metadatas[i].get("research_areas", []),
            "score": round(1 - distances[i], 2)
        })

    return formatted


# -----------------------------
# MAIN AGENT CONTROLLER
# -----------------------------
def start_agent():

    print("\n===================================")
    print("RESEARCH MATCHING CHATBOT")
    print("===================================")

    mode = input("Choose mode (student/professor): ").lower()

    collection = get_collection()

    query = input("\nEnter your research interest: ")

    # 1. Convert query → embedding
    query_embedding = embed_text(query)

    # 2. Retrieve from ChromaDB
    raw_results = retrieve_faculty(query_embedding, collection)

    # 3. Format results
    rag_results = recommend_faculty(query, format_results(raw_results))

    # -----------------------------
    # STUDENT MODE
    # -----------------------------
    if mode == "student":

        print("\n🏆 TOP MATCHES:\n")

        for i, faculty in enumerate(rag_results[:3], 1):

            print(f"{i}. {faculty['name']}")
            print("   Department:", faculty["department"])
            print("   Score:", faculty["score"])

            print("   Why this match:")
            for reason in explain_match(query, faculty):
                print("   -", reason)

            print("\n" + "-" * 50)

        name = input("\nEnter faculty name for details: ")
        tell_about_faculty(name, rag_results)

    # -----------------------------
    # PROFESSOR MODE
    # -----------------------------
    elif mode == "professor":

        professor_mode(rag_results)

    else:
        print("Invalid mode selected")
