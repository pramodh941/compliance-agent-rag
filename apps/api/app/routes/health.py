from fastapi import APIRouter
from app.dependencies.postgres import get_postgres_connection
from app.dependencies.qdrant import get_qdrant_client

router = APIRouter()

@router.get("/health")
def health_check():
    # Postgres check
    try:
        conn = get_postgres_connection()
        conn.close()
        pg_status = "ok"
    except:
        pg_status = "fail"

    # Qdrant check
    try:
        client = get_qdrant_client()
        client.get_collections()
        qdrant_status = "ok"
    except:
        qdrant_status = "fail"

    return {
        "api": "ok",
        "postgres": pg_status,
        "qdrant": qdrant_status
    }