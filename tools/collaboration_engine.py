def find_collaborations(faculty_list):

    collaborations = []

    for i in range(len(faculty_list)):

        for j in range(i + 1, len(faculty_list)):

            f1 = faculty_list[i]
            f2 = faculty_list[j]

            common = set(f1.get("research_areas", [])) & set(f2.get("research_areas", []))

            if common:

                collaborations.append({
                    "faculty_1": f1["name"],
                    "faculty_2": f2["name"],
                    "shared_area": list(common)
                })

    return collaborations