def find_gaps(rag_results, trending_topics):

    faculty_topics = set()

    for faculty in rag_results:
        for area in faculty["research_areas"]:
            faculty_topics.add(area)

    print("\n==============================")
    print("RESEARCH GAP ANALYSIS")
    print("==============================")

    gaps = []

    for topic in trending_topics:
        if topic not in faculty_topics:
            gaps.append(topic)

    if len(gaps) == 0:
        print("No research gaps found.")

    else:
        print("Department should explore:\n")

        for gap in gaps:
            print("-", gap)

    return gaps


if __name__ == "__main__":

    rag_results = [

        {
            "name": "Dr. Ramesh",
            "research_areas": [
                "Artificial Intelligence",
                "Machine Learning"
            ]
        },

        {
            "name": "Dr. Priya",
            "research_areas": [
                "Computer Vision",
                "Deep Learning"
            ]
        }

    ]

    trending_topics = [

        "Artificial Intelligence",
        "Machine Learning",
        "Agentic AI",
        "RAG Systems",
        "Multimodal LLMs"

    ]

    find_gaps(rag_results, trending_topics)