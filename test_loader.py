from agents.data_loader import load_faculty

faculty = load_faculty()

print("Total Faculty:", len(faculty))

print("\nFirst Faculty:")
print("Name:", faculty[0]["Identity"]["Name"])
print("Department:", faculty[0]["Identity"]["Department"])
print("Research Areas:", faculty[0]["ResearchIntelligence"]["ResearchAreas"])