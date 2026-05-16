from fastapi import APIRouter, Request
from app.dependencies.postgres import get_postgres_connection
from app.dependencies.qdrant import get_qdrant_client
from app.core.config import settings
from app.core.ingestion_config import IngestionConfig
from app.core.logging import get_logger
import requests

router = APIRouter()
logger = get_logger(__name__)


@router.get("/health")
def health_check():
    # Postgres check
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        pg_status = "ok"
    except Exception as e:
        pg_status = f"fail: {str(e)}"

    # Qdrant check
    try:
        client = get_qdrant_client()
        client.get_collections()
        qdrant_status = "ok"
    except Exception as e:
        qdrant_status = f"fail: {str(e)}"

    # Ollama check (optional - don't fail health if Ollama is down)
    ollama_status = "not_checked"
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
        ollama_status = "ok" if response.status_code == 200 else "degraded"
    except Exception:
        ollama_status = "unavailable"

    # Reranker check (optional - don't fail health if reranker is down)
    reranker_status = "not_checked"
    try:
        response = requests.get("http://reranker:7997/health", timeout=2)
        reranker_status = "ok" if response.status_code == 200 else "degraded"
    except Exception:
        reranker_status = "unavailable"

    return {
        "api": "ok",
        "postgres": pg_status,
        "qdrant": qdrant_status,
        "ollama": ollama_status,
        "reranker": reranker_status,
        "status": "healthy" if pg_status == "ok" and qdrant_status == "ok" else "degraded"
    }


@router.get("/diagnostics")
def diagnostics(request: Request):
    """Operational diagnostics endpoint with configuration and system info."""
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    # Get cache stats
    from app.services.cache import get_cache
    cache_instance = get_cache()
    cache_size = len(cache_instance.store) if hasattr(cache_instance, 'store') else 0
    
    # Get BM25 corpus stats
    from app.services.hybrid_retriever import hybrid_retriever
    bm25_corpus_size = len(hybrid_retriever.corpus) if hasattr(hybrid_retriever, 'corpus') else 0
    
    # Get ingestion config
    ingestion_config = IngestionConfig()
    
    return {
        "correlation_id": correlation_id,
        "timestamp": logger.info("Diagnostics requested", extra={"correlation_id": correlation_id}),
        "system": {
            "log_level": settings.LOG_LEVEL,
            "api_timeout": settings.API_REQUEST_TIMEOUT,
            "agent_timeout": settings.AGENT_RUN_TIMEOUT
        },
        "rag_config": {
            "dense_retrieval_limit": settings.DENSE_RETRIEVAL_LIMIT,
            "sparse_retrieval_k": settings.SPARSE_RETRIEVAL_K,
            "rerank_top_k": settings.RERANK_TOP_K,
            "max_context_length": settings.MAX_CONTEXT_LENGTH,
            "max_embedding_chars": settings.MAX_EMBEDDING_CHARS,
            "enable_reranking": settings.ENABLE_RERANKING
        },
        "ingestion_config": ingestion_config.get_summary(),
        "cache": {
            "size": cache_size,
            "ttl_seconds": cache_instance.ttl if hasattr(cache_instance, 'ttl') else 300
        },
        "retrieval": {
            "bm25_corpus_size": bm25_corpus_size,
            "bm25_initialized": hybrid_retriever.bm25 is not None if hasattr(hybrid_retriever, 'bm25') else False
        },
        "endpoints": {
            "health": "/health",
            "diagnostics": "/diagnostics",
            "qa": "/qa",
            "scan_email": "/scan-email",
            "agents_run": "/agents/run",
            "ingest": "/ingest",
            "ingest_status": "/ingest/status",
            "ingest_config": "/ingest/config"
        }
    }