from fastapi import APIRouter, Query
from typing import Optional
from app.dependencies.postgres import get_postgres_connection

router = APIRouter()

@router.get("/alerts")
def get_alerts(limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of alerts to return (1-1000)")):
    """Get alerts with optional limit parameter."""
    conn = get_postgres_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, email_id, rule_type, message, created_at FROM alerts ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [
        {
            "id": r[0],
            "email_id": r[1],
            "rule_type": r[2],
            "message": r[3],
            "created_at": r[4]
        }
        for r in rows
    ]