import os
from dotenv import load_dotenv
import requests

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search_trends(query: str):

    if not TAVILY_API_KEY:
        return "Tavily API key not found. Please check .env file."

    url = "https://api.tavily.com/search"

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": True
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()

        return (
            data.get("answer")
            or data.get("results", [{}])[0].get("content", "No trend found")
        )

    return f"Tavily API error: {response.status_code}"