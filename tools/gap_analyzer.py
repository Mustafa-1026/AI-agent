def analyze_gaps(faculty_list, trending_topics):

    covered = set()

    for faculty in faculty_list:
        for area in faculty.get("research_areas", []):
            covered.add(area.lower())

    gaps = []

    for topic in trending_topics:
        if topic.lower() not in covered:
            gaps.append(topic)

    return gaps