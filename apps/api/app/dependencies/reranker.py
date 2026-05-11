import requests
from app.core.config import settings
from app.core.logging import get_logger
from app.core.retry import retry_on_exception

logger = get_logger(__name__)

RERANKER_URL = "http://compliance-reranker:7997/rerank"


@retry_on_exception(
    max_retries=2,
    base_delay=0.5,
    max_delay=2.0,
    exceptions=(requests.exceptions.ConnectionError, requests.exceptions.Timeout)
)
def rerank(query: str, documents: list[str]) -> list[dict]:
    if not documents:
        return []

    try:
        response = requests.post(
            RERANKER_URL,
            json={
                "query": query,
                "documents": documents
            },
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        results = data.get("results", [])

        ranked = sorted(
            results,
            key=lambda x: x.get("relevance_score", 0),
            reverse=True
        )

        return [
            {
                "text": documents[r["index"]],
                "score": r.get("relevance_score", 0)
            }
            for r in ranked if "index" in r
        ]

    except Exception as e:
        print(f"[reranker error] {e}")

        # ✅ FIX: return SAME STRUCTURE
        return [
            {"text": doc, "score": 0}
            for doc in documents
        ]