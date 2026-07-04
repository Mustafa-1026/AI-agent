from agents.collaboration import find_collaboration
from agents.gap_analysis import find_gaps

def professor_mode(rag_results):

    print("\n===================================")
    print("PROFESSOR MODE")
    print("===================================")

    topic = input("Enter research topic: ")

    print("\nSearching latest research trends...")

    # Temporary trends
    trending_topics = [

        "Artificial Intelligence",
        "Machine Learning",
        "Agentic AI",
        "RAG Systems",
        "Multimodal LLMs"

    ]

    print("\nLatest Trends")

    for trend in trending_topics:
        print("-", trend)

    print("\nChecking collaboration opportunities...")

    find_collaboration(rag_results)

    print("\nChecking research gaps...")

    find_gaps(rag_results, trending_topics)


if __name__ == "__main__":

    rag_results = [

        {
            "name": "Dr. Ramesh Karnati",
            "research_areas": [
                "Artificial Intelligence",
                "Machine Learning"
            ]
        },

        {
            "name": "Dr. Priya",
            "research_areas": [
                "Artificial Intelligence",
                "Computer Vision"
            ]
        },

        {
            "name": "Dr. Vinay",
            "research_areas": [
                "IoT",
                "Data Mining"
            ]
        }

    ]

    professor_mode(rag_results)