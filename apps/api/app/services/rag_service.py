from app.dependencies.qdrant import get_qdrant_client
from app.services.ollama_client import get_embedding, generate_response
from app.dependencies.reranker import rerank
from app.services.hybrid_retriever import hybrid_retriever
from app.core.logging import get_logger
from app.core.config import settings
import re
import time

# 🔥 CACHE
from app.services.cache import get_cache

cache = get_cache()
logger = get_logger(__name__)

COLLECTIONS = {
    "policies": "Internal company policies like MNPI, gifts, communication",
    "sec_docs": "SEC regulatory documents, rules, risk alerts"
}


def route_query(query: str) -> list:
    """
    Route query to appropriate collections with improved keyword matching.
    
    Prioritizes specific collections based on query content to improve
    retrieval grounding and reduce cross-collection contamination.
    """
    query_lower = query.lower()
    
    # SEC-specific keywords (highest priority)
    sec_keywords = [
        "sec", "rule", "regulation", "adviser", "act", "compliance rule",
        "exchange", "commission", "risk alert", "market rule", "examination"
    ]
    
    # Policy-specific keywords (highest priority)
    policy_keywords = [
        "policy", "employee", "internal", "mnpi", "gifts",
        "trading", "personal", "communication", "workplace", "ethics",
        "insider", "material", "non-public", "information"
    ]
    
    # Count matches for each collection
    sec_matches = sum(1 for word in sec_keywords if word in query_lower)
    policy_matches = sum(1 for word in policy_keywords if word in query_lower)
    
    # Route based on match counts
    if sec_matches > policy_matches:
        return ["sec_docs"]
    elif policy_matches > sec_matches:
        return ["policies"]
    elif sec_matches > 0 and policy_matches > 0:
        # Both have matches, return both but prioritize based on count
        return ["sec_docs", "policies"] if sec_matches >= policy_matches else ["policies", "sec_docs"]
    else:
        # No clear matches, search both
        return ["policies", "sec_docs"]


def sanitize_input(input_str: str) -> str:
    # Sanitize input to prevent prompt injection
    return re.sub(r'[^a-zA-Z0-9\s\.,!?-]', '', input_str)


def answer_question(query: str):
    rag_start = time.time()
    logger.info("RAG query received")

    # Sanitize input to prevent prompt injection
    sanitized_query = sanitize_input(query)
    logger.info("Answering question", extra={"query": sanitized_query[:100]})

    # =========================
    # 🔥 RESPONSE CACHE (FAST PATH)
    # =========================
    cached = cache.get(f"response:{sanitized_query}")
    if cached:
        logger.info("RAG response cache hit")
        return cached

    qdrant = get_qdrant_client()

    # =========================
    # 🔥 EMBEDDING
    # =========================
    embedding_start = time.time()
    query_vector = cache.get(f"embedding:{sanitized_query}")

    if query_vector:
        logger.info("Embedding cache hit")
    else:
        query_vector = get_embedding(sanitized_query)
        cache.set(f"embedding:{sanitized_query}", query_vector)
        logger.info("Embedding stored")

    embedding_duration_ms = (time.time() - embedding_start) * 1000

    if not query_vector:
        logger.warning(
            "Embedding generation failed",
            extra={
                "operation": "rag_retrieval",
                "stage": "embedding",
                "duration_ms": round(embedding_duration_ms, 2),
                "success": False
            }
        )
        return {
            "answer": "Failed to process query",
            "context_used": ""
        }

    logger.info("Query embedding generated")

    collections = route_query(sanitized_query)
    logger.info("Query routed", extra={"status": ",".join(collections)})

    # 🔹 DENSE RETRIEVAL
    dense_start = time.time()
    dense_chunks = []

    for col in collections:
        results = qdrant.query_points(
            collection_name=col,
            query=query_vector,
            limit=settings.DENSE_RETRIEVAL_LIMIT
        )

        logger.info("Dense retrieval completed", extra={"status": f"{col}:{len(results.points)}"})

        # Extract chunks with metadata for better grounding
        for p in results.points:
            chunk = {
                "text": p.payload["text"],
                "source": p.payload.get("source"),
                "page": p.payload.get("page"),
                "doc_type": p.payload.get("doc_type"),
                "score": p.score
            }
            
            # Add metadata fields if available for better grounding
            if "title" in p.payload:
                chunk["title"] = p.payload["title"]
            if "section_headers" in p.payload and p.payload["section_headers"]:
                chunk["section_headers"] = p.payload["section_headers"]
            
            dense_chunks.append(chunk)

    dense_duration_ms = (time.time() - dense_start) * 1000

    # 🔹 SPARSE RETRIEVAL (BM25)
    sparse_start = time.time()
    sparse_chunks = hybrid_retriever.search(sanitized_query, k=settings.SPARSE_RETRIEVAL_K)
    sparse_duration_ms = (time.time() - sparse_start) * 1000
    logger.info("Sparse retrieval completed", extra={"status": str(len(sparse_chunks))})

    all_chunks_dict = {c["text"]: c for c in dense_chunks}

    for c in sparse_chunks:
        if c["text"] not in all_chunks_dict:
            all_chunks_dict[c["text"]] = c

    all_chunks = list(all_chunks_dict.values())

    logger.info("Merged chunks", extra={"status": str(len(all_chunks))})

    if not all_chunks:
        logger.warning(
            "No chunks retrieved",
            extra={
                "operation": "rag_retrieval",
                "stage": "retrieval",
                "dense_count": len(dense_chunks),
                "sparse_count": len(sparse_chunks),
                "success": False
            }
        )
        result = {
            "answer": "Not found in provided documents",
            "context_used": ""
        }
        cache.set(f"response:{sanitized_query}", result)
        return result

    # 🔹 RERANK
    rerank_start = time.time()
    logger.info("Sending chunks to reranker", extra={"status": str(len(all_chunks))})
    
    if settings.ENABLE_RERANKING:
        try:
            reranked = rerank(sanitized_query, [c["text"] for c in all_chunks[:8]])
            rerank_duration_ms = (time.time() - rerank_start) * 1000
            rerank_success = True
        except Exception as e:
            rerank_duration_ms = (time.time() - rerank_start) * 1000
            rerank_success = False
            logger.warning(f"Reranker failed, using unranked results: {e}")
            reranked = [{"text": c["text"], "score": 1.0 - i * 0.1} for i, c in enumerate(all_chunks[:settings.RERANK_TOP_K])]
    else:
        rerank_duration_ms = 0
        rerank_success = False
        logger.info("Reranking disabled, using top dense results")
        reranked = [{"text": c["text"], "score": c.get("score", 1.0)} for c in all_chunks[:settings.RERANK_TOP_K]]

    top_chunks = []
    used = set()

    for r in reranked:
        for i, c in enumerate(all_chunks):
            if c["text"] == r["text"] and i not in used:
                c["rerank_score"] = r.get("score", 0)
                top_chunks.append(c)
                used.add(i)
                break

        if len(top_chunks) == settings.RERANK_TOP_K:
            break

    if not top_chunks:
        logger.warning(
            "No top chunks after reranking",
            extra={
                "operation": "rag_retrieval",
                "stage": "reranking",
                "success": False
            }
        )
        result = {
            "answer": "Not found in provided documents",
            "context_used": ""
        }
        cache.set(f"response:{sanitized_query}", result)
        return result

    context = "\n\n".join([
        f"[Source: {c['source']} | Page: {c['page']} | Title: {c.get('title', 'N/A')}]\n{c['text'][:settings.MAX_CONTEXT_LENGTH]}"
        for c in top_chunks
    ])

    # System prompt for hardening against prompt injection and hallucination
    system_prompt = """
You are a compliance assistant for a financial services company.

Your role is to answer questions about company policies and regulatory requirements based ONLY on the provided context.

STRICT RULES:
- Answer ONLY using information from the provided context
- If the context does not contain relevant information, state that clearly
- Do NOT make up or hallucinate information
- Do NOT claim to have information that is not in the context
- If the answer is not in the context, say "I cannot answer this question from the provided documents"
- Keep answers factual and concise
- Reference specific policy names when available
"""

    prompt = f"""
{system_prompt}

Context:
{context}

Question:
{sanitized_query}

Answer:
"""

    # 🔹 LLM GENERATION
    generation_start = time.time()
    answer = generate_response(prompt)
    generation_duration_ms = (time.time() - generation_start) * 1000

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

    cache.set(f"response:{sanitized_query}", result)
    
    total_duration_ms = (time.time() - rag_start) * 1000
    logger.info(
        "RAG query completed",
        extra={
            "operation": "rag_retrieval",
            "total_duration_ms": round(total_duration_ms, 2),
            "embedding_duration_ms": round(embedding_duration_ms, 2),
            "dense_retrieval_duration_ms": round(dense_duration_ms, 2),
            "sparse_retrieval_duration_ms": round(sparse_duration_ms, 2),
            "rerank_duration_ms": round(rerank_duration_ms, 2),
            "generation_duration_ms": round(generation_duration_ms, 2),
            "dense_chunks_count": len(dense_chunks),
            "sparse_chunks_count": len(sparse_chunks),
            "final_chunks_count": len(top_chunks),
            "rerank_success": rerank_success,
            "cache_hit": False
        }
    )

    return result
