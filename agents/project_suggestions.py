def suggest_projects(faculty):

    research = faculty["research_areas"]

    print("\n===== PROJECT SUGGESTIONS =====")

    if "Artificial Intelligence" in research:
        print("- AI Chatbot using RAG")

    if "Machine Learning" in research:
        print("- Student Performance Prediction")

    if "Computer Vision" in research:
        print("- Face Recognition Attendance System")

    if "Deep Learning" in research:
        print("- Medical Image Classification")

    if "IoT" in research:
        print("- Smart Home Automation")

    if "Data Mining" in research:
        print("- Student Data Analytics")

    if "Cyber Security" in research:
        print("- Phishing Detection System")