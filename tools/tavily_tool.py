import os
import requests
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


def search_trends(query: str):
    """
    Search the latest research trends using Tavily.

    Args:
        query (str): Research topic.

    Returns:
        str: Summary of latest trends or an error message.
    """

    if not TAVILY_API_KEY:
        return "Tavily API key not found. Please check your .env file."

    url = "https://api.tavily.com/search"

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": 5
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("answer"):
            return data["answer"]

        results = data.get("results", [])

        if results:
            return results[0].get("content", "No trend found.")

        return "No trend found."

    except requests.exceptions.RequestException as e:
        return f"Tavily API error: {e}"