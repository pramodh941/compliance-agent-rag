from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding, generate_response
from app.dependencies.reranker import rerank

COLLECTIONS = {
    "policies": "Internal company policies like MNPI, gifts, communication",
    "sec_docs": "SEC regulatory documents, rules, risk alerts"
}

def route_query(query: str) -> list:
    query_lower = query.lower()

    if any(word in query_lower for word in [
        "sec", "rule", "regulation", "adviser", "act", "compliance rule"
    ]):
        return ["sec_docs"]

    if any(word in query_lower for word in [
        "policy", "employee", "internal", "mnpi", "gifts"
    ]):
        return ["policies"]

    # fallback → search both
    return ["policies", "sec_docs"]

def answer_question(query: str):
    print(f"\n[RAG] Incoming query: {query}")
    qdrant = get_qdrant_client()

    # 1. Embed query
    query_vector = get_embedding(query)
    if not query_vector:
        return {
            "answer": "Failed to process query",
            "context_used": ""
        }
    print(f"[RAG] Query embedding generated: {'yes' if query_vector else 'no'}")

    collections = route_query(query)
    print(f"[RAG] Routed to collections: {collections}")

    all_points = []

    # 2. Retrieve from all relevant collections
    for col in collections:
        results = qdrant.query_points(
            collection_name=col,
            query=query_vector,
            limit=5
        )
        print(f"[RAG] Retrieved {len(results.points)} points from {col}")
        all_points.extend(results.points)

    print(f"[RAG] Total retrieved points: {len(all_points)}")

    # 3. Handle no results AFTER loop
    if not all_points:
        print("[RAG] No results found")
        return {
            "answer": "Not found in provided documents",
            "context_used": ""
        }

    # 4. Extract text + metadata (IMPORTANT UPGRADE 🔥)
    chunks = [
        {
            "text": p.payload["text"],
            "source": p.payload.get("source"),
            "page": p.payload.get("page"),
            "doc_type": p.payload.get("doc_type"),
            "score": p.score
        }
        for p in all_points
    ]

    # 5. Rerank (pass only text to model)
    print(f"[RAG] Sending {len(chunks)} chunks to reranker")
    reranked = rerank(query, [c["text"] for c in chunks[:6]])
    print(f"[RAG] Reranker returned {len(reranked)} results")

    top_chunks = []
    used = set()

    for r in reranked:
        for i, c in enumerate(chunks):
            if c["text"] == r["text"] and i not in used:
                c["rerank_score"] = r["score"]  # optional but useful
                top_chunks.append(c)
                used.add(i)
                break

        if len(top_chunks) == 2:
            break
    
    if not top_chunks:
        print("[RAG] No top chunks after reranking")
        return {
            "answer": "Not found in provided documents",
            "context_used": ""
        }

    # 7. Build context with traceability
    context = "\n\n".join([
        f"[Source: {c['source']} | Page: {c['page']}]\n{c['text'][:400]}"
        for c in top_chunks
    ])

    # 8. Prompt
    prompt = f"""
You are a compliance assistant.

Use ONLY the provided context to answer the question.

Rules:
- Do NOT use outside knowledge
- If the answer is not explicitly present, say: "Not found in provided documents"
- Be precise and cite the source if possible

Context:
{context}

Question:
{query}

Answer:
"""

    answer = generate_response(prompt)

    return {
        "answer": answer,
        "context_used": context
    }