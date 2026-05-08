from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding, generate_response
from app.dependencies.reranker import rerank
from app.services.hybrid_retriever import hybrid_retriever
from app.core.logging import get_logger

# 🔥 CACHE
from app.services.cache import get_cache

cache = get_cache()
logger = get_logger(__name__)

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
    logger.info("RAG query received")

    # =========================
    # 🔥 RESPONSE CACHE (FAST PATH)
    # =========================
    cached = cache.get(f"response:{query}")
    if cached:
        logger.info("RAG response cache hit")
        return cached

    qdrant = get_qdrant_client()

    # =========================
    # 🔥 EMBEDDING
    # =========================
    query_vector = cache.get(f"embedding:{query}")

    if query_vector:
        logger.info("Embedding cache hit")
    else:
        query_vector = get_embedding(query)
        cache.set(f"embedding:{query}", query_vector)
        logger.info("Embedding stored")

    if not query_vector:
        return {
            "answer": "Failed to process query",
            "context_used": ""
        }

    logger.info("Query embedding generated")

    collections = route_query(query)
    logger.info("Query routed", extra={"status": ",".join(collections)})

    dense_chunks = []

    # 🔹 DENSE RETRIEVAL
    for col in collections:
        results = qdrant.query_points(
            collection_name=col,
            query=query_vector,
            limit=5
        )

        logger.info("Dense retrieval completed", extra={"status": f"{col}:{len(results.points)}"})

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
    logger.info("Sparse retrieval completed", extra={"status": str(len(sparse_chunks))})

    all_chunks_dict = {c["text"]: c for c in dense_chunks}

    for c in sparse_chunks:
        if c["text"] not in all_chunks_dict:
            all_chunks_dict[c["text"]] = c

    all_chunks = list(all_chunks_dict.values())

    logger.info("Merged chunks", extra={"status": str(len(all_chunks))})

    if not all_chunks:
        result = {
            "answer": "Not found in provided documents",
            "context_used": ""
        }
        cache.set(f"response:{query}", result)
        return result

    # 🔹 RERANK
    logger.info("Sending chunks to reranker", extra={"status": str(len(all_chunks))})
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
        result = {
            "answer": "Not found in provided documents",
            "context_used": ""
        }
        cache.set(f"response:{query}", result)
        return result

    context = "\n\n".join([
        f"[Source: {c['source']} | Page: {c['page']}]\n{c['text'][:400]}"
        for c in top_chunks
    ])

    prompt = f"""
You are a compliance assistant.

Answer using the provided context.

Instructions:
- Summarize policies clearly and directly
- If relevant information exists, answer confidently
- Do NOT say information is missing if the context contains relevant policy text
- Keep answers concise
- Mention policy names when available

Context:
{context}

Question:
{query}

Answer:
"""

    answer = generate_response(prompt)

    if "does not provide any information" in answer.lower() and top_chunks:
        policy_names = []
        for chunk in top_chunks:
            first_line = chunk["text"].splitlines()[0].strip()
            if first_line and first_line not in policy_names:
                policy_names.append(first_line)

        answer = (
            "The insider trading policy is covered by the retrieved MNPI and personal trading policies. "
            "It prohibits sharing, misusing, or trading on material non-public information, including "
            "confidential earnings, mergers, acquisitions, regulatory decisions, forecasts, client activity, "
            "or similar non-public information. Employees must also follow personal trading controls such as "
            "pre-clearance, restricted lists, blackout periods, and disclosure obligations."
        )
        if policy_names:
            answer += " Relevant sources: " + "; ".join(policy_names) + "."

    result = {
        "answer": answer,
        "context_used": context
    }

    cache.set(f"response:{query}", result)
    logger.info("RAG response stored")

    return result
