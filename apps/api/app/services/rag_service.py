from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding, generate_response

COLLECTION_NAME = "policies"

def answer_question(query: str):
    qdrant = get_qdrant_client()

    # embed query
    query_vector = get_embedding(query)

    # retrieve top matches
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=2
    )

    points = results.points

    # build context
    context = "\n".join([p.payload["text"] for p in points])

    # prompt
    prompt = f"""
You are a compliance assistant.
Based ONLY on the context below, answer the question in 2-3 sentences.
Context:
{context}

Question:
{query}

Answer:
"""

    # generate answer via Ollama
    return {
        "answer": generate_response(prompt),
        "context_used": context
    }