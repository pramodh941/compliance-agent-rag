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

Use the provided context to answer the question.

Rules:
- You MUST base your answer on the context
- You CAN infer logical conclusions from the context
- Be clear and direct
- If the answer is not present at all, say: "Not found in provided policies"

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