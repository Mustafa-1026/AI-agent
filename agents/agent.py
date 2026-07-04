from agents.student_agent import show_best_match, tell_about_faculty
from agents.professor_agent import professor_mode


def start_agent():

    print("\n===================================")
    print("RESEARCH MATCHING CHATBOT")
    print("===================================")

    mode = input("Choose mode (student/professor): ").lower()

    # Temporary data
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
                "Artificial Intelligence",
                "Computer Vision"
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

    if mode == "student":

        show_best_match(rag_results)

        name = input("\nEnter faculty name for details: ")
        tell_about_faculty(name, rag_results)

    elif mode == "professor":

        professor_mode(rag_results)

    else:

        print("Invalid mode")


if __name__ == "__main__":

    start_agent()