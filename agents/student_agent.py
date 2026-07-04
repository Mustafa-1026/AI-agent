from agents.project_suggestions import suggest_projects


def show_best_match(rag_results):

    if len(rag_results) == 0:
        print("No faculty found.")
        return

    current = 0

    while True:

        faculty = rag_results[current]

        print("\n==============================")
        print("FACULTY", current + 1)
        print("==============================")
        print("Name       :", faculty["name"])
        print("Department :", faculty["department"])
        print("Research   :", ", ".join(faculty["research_areas"]))
        print("Score      :", faculty["score"])

        # Show project suggestions
        suggest_projects(faculty)

        choice = input("\nType 'next' for another faculty or 'exit': ")

        if choice.lower() == "next":

            if current + 1 < len(rag_results):
                current += 1
            else:
                print("\nNo more faculty available.")

        elif choice.lower() == "exit":
            break

        else:
            print("Invalid input")


def tell_about_faculty(name, rag_results):

    for faculty in rag_results:

        if faculty["name"].lower() == name.lower():

            print("\n==============================")
            print("FACULTY DETAILS")
            print("==============================")
            print("Name       :", faculty["name"])
            print("Department :", faculty["department"])
            print("Research   :", ", ".join(faculty["research_areas"]))
            print("Score      :", faculty["score"])

            # Show projects here also
            suggest_projects(faculty)

            return

    print("Faculty not found.")


if __name__ == "__main__":

    rag_results = [

        {
            "name": "Dr. Ramesh Karnati",
            "department": "CSE",
            "research_areas": [
                "Artificial Intelligence",
                "Machine Learning"
            ],
            "score": 0.95
        },

        {
            "name": "Dr. Priya",
            "department": "CSE",
            "research_areas": [
                "Computer Vision",
                "Deep Learning"
            ],
            "score": 0.90
        },

        {
            "name": "Dr. Vinay",
            "department": "CSE",
            "research_areas": [
                "IoT",
                "Data Mining"
            ],
            "score": 0.87
        }

    ]

    show_best_match(rag_results)

    name = input("\nEnter faculty name: ")
    tell_about_faculty(name, rag_results)