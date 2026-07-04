from agents.data_loader import load_faculty

def search_faculty(topic):

    faculty_list = load_faculty()

    results = []

    topic = topic.lower()

    for faculty in faculty_list:

        areas = faculty["ResearchIntelligence"]["ResearchAreas"]

        for area in areas:

            if topic in area.lower():

                results.append(faculty)

                break

    return results


if __name__ == "__main__":

    topic = input("Enter topic: ")

    matches = search_faculty(topic)

    print("\nMatches Found:", len(matches))

    for faculty in matches:

        print("--------------------------------")
        print("Name:", faculty["Identity"]["Name"])
        print("Department:", faculty["Identity"]["Department"])
        print("Research Areas:", faculty["ResearchIntelligence"]["ResearchAreas"])