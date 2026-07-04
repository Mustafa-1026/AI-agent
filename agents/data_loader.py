import json

def load_faculty():

    with open("data/faculty_profiles.json", "r", encoding="utf-8") as file:
        faculty = json.load(file)

    return faculty