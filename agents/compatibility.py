def compute_score(query, faculty):

    score = 0
    query = query.lower()

    for area in faculty.get("research_areas", []):
        if area.lower() in query:
            score += 0.5

    if faculty.get("department", "").lower() in query:
        score += 0.2

    return min(score, 1.0)