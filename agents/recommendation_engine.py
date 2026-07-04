from agents.compatibility import compute_score

def recommend_faculty(query, faculty_list):

    results = []

    for faculty in faculty_list:
        score = compute_score(query, faculty)

        results.append({
            "faculty": faculty,
            "score": score
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results