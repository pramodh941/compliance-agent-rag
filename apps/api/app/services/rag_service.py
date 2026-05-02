from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding, generate_response
from app.dependencies.reranker import rerank

COLLECTION_NAME = "policies"


def answer_question(query: str):
    qdrant = get_qdrant_client()

    # 1. Embed query
    query_vector = get_embedding(query)

    # 2. Retrieve MORE candidates (important for reranking to work well)
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=10  # 🔥 increase from 2 → 10
    )

    points = results.points

    if not points:
        return {
            "answer": "Not found in provided policies",
            "context_used": ""
        }

    # 3. Extract raw texts
    chunks = [p.payload["text"] for p in points]

    # 4. Rerank using cross-encoder (Infinity service)
    reranked_chunks = rerank(query, chunks)

    # 5. Keep top-k after reranking
    top_chunks = reranked_chunks[:3]

    # 6. Build final context
    context = "\n\n".join(top_chunks)

    # 7. Prompt engineering
    prompt = f"""
You are a compliance assistant.

Use ONLY the provided context to answer the question.

Rules:
- Base your answer strictly on the context
- If partially relevant, infer carefully
- If not found, say: "Not found in provided policies"

Context:
{context}

Question:
{query}

Answer:
"""

    # 8. Generate response
    answer = generate_response(prompt)

    return {
        "answer": answer,
        "context_used": context
    }