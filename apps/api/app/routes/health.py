from fastapi import APIRouter
from app.dependencies.postgres import get_postgres_connection
from app.dependencies.qdrant import get_qdrant_client
from app.core.config import settings
import requests

router = APIRouter()

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