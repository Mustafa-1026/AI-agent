def find_collaboration(rag_results):

    print("\n==============================")
    print("COLLABORATION SUGGESTIONS")
    print("==============================")

    if len(rag_results) < 2:
        print("Not enough faculty for collaboration.")
        return

    for i in range(len(rag_results)):
        for j in range(i + 1, len(rag_results)):

            common = set(rag_results[i]["research_areas"]) & set(rag_results[j]["research_areas"])

            if common:

                print(f"\n{rag_results[i]['name']}  <-->  {rag_results[j]['name']}")
                print("Common Area:", ", ".join(common))

if __name__ == "__main__":

    faculty = [

        {
            "name":"Dr. Ramesh",
            "research_areas":["AI","ML","IoT"]
        },

        {
            "name":"Dr. Priya",
            "research_areas":["AI","Computer Vision"]
        }

    ]

    find_collaboration(faculty)