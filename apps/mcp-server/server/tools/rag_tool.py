from ..registry import register_tool
import requests

@register_tool("rag_search")
def rag_search(input: dict):
    query = input.get("query")

    res = requests.post(
        "http://api:8000/qa",
        params={"query": query},
        timeout=30
    )

    return res.json()