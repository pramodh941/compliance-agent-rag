from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding, generate_response
from app.dependencies.reranker import rerank

# 🔥 NEW
from app.services.hybrid_retriever import hybrid_retriever

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

    print(f"[RAG] Query embedding generated: yes")

    collections = route_query(query)
    print(f"[RAG] Routed to collections: {collections}")

    dense_chunks = []

    # 🔹 DENSE RETRIEVAL
    for col in collections:
        results = qdrant.query_points(
            collection_name=col,
            query=query_vector,
            limit=5
        )

        print(f"[RAG] Retrieved {len(results.points)} points from {col}")

        dense_chunks.extend([
            {
                "text": p.payload["text"],
                "source": p.payload.get("source"),
                "page": p.payload.get("page"),
                "doc_type": p.payload.get("doc_type"),
                "score": p.score
            }
            for p in results.points
        ])

    # 🔹 SPARSE RETRIEVAL (BM25)
    sparse_chunks = hybrid_retriever.search(query, k=5)
    print(f"[RAG] Retrieved {len(sparse_chunks)} BM25 chunks")

    # 🔹 MERGE + DEDUPE
    all_chunks_dict = {
        c["text"]: c for c in dense_chunks
    }

    for c in sparse_chunks:
        if c["text"] not in all_chunks_dict:
            all_chunks_dict[c["text"]] = c

    all_chunks = list(all_chunks_dict.values())

    print(f"[RAG] Total merged chunks: {len(all_chunks)}")

    if not all_chunks:
        return {
            "answer": "Not found in provided documents",
            "context_used": ""
        }

    # 🔹 RERANK
    print(f"[RAG] Sending {len(all_chunks)} chunks to reranker")
    reranked = rerank(query, [c["text"] for c in all_chunks[:8]])

    top_chunks = []
    used = set()

    for r in reranked:
        for i, c in enumerate(all_chunks):
            if c["text"] == r["text"] and i not in used:
                c["rerank_score"] = r.get("score", 0)
                top_chunks.append(c)
                used.add(i)
                break

        if len(top_chunks) == 2:
            break

    if not top_chunks:
        return {
            "answer": "Not found in provided documents",
            "context_used": ""
        }

    # 🔹 CONTEXT
    context = "\n\n".join([
        f"[Source: {c['source']} | Page: {c['page']}]\n{c['text'][:400]}"
        for c in top_chunks
    ])

    # 🔹 PROMPT
    prompt = f"""
You are a compliance assistant.

Answer the question using ONLY the provided context.

Rules:
- Use the context to infer answers when possible (do NOT require exact sentence match)
- If the answer is partially available, summarize it clearly
- Only say "Not found in provided documents" if there is truly no relevant information
- Always be concise and factual
- Cite source and page when possible

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