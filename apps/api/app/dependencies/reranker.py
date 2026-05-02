import requests

RERANKER_URL = "http://compliance-reranker:7997/rerank"


def rerank(query: str, documents: list[str]) -> list[str]:
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

        # IMPORTANT: index maps back to original docs
        return [documents[r["index"]] for r in ranked if "index" in r]

    except Exception as e:
        print(f"[reranker error] {e}")
        return documents