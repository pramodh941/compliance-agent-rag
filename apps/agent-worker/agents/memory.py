import json
import os
from datetime import datetime, timezone

import psycopg2


SESSION_MEMORY = {}


def _connect():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "admin"),
        password=os.getenv("POSTGRES_PASSWORD", "admin"),
        dbname=os.getenv("POSTGRES_DB", "compliance"),
    )


def _ensure_schema():
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id VARCHAR(100) PRIMARY KEY,
            user_id VARCHAR(100),
            started_at TIMESTAMP DEFAULT NOW(),
            last_accessed TIMESTAMP DEFAULT NOW(),
            status VARCHAR(20) DEFAULT 'active',
            conversation_history JSONB DEFAULT '[]'::jsonb,
            tool_calls JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id BIGSERIAL PRIMARY KEY,
            session_id VARCHAR(100),
            action VARCHAR(100),
            details JSONB,
            timestamp TIMESTAMP DEFAULT NOW()
        )
        """
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_memory(session_id: str):
    try:
        _ensure_schema()
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT conversation_history FROM sessions WHERE id = %s",
            (session_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return []
        return row[0] or []
    except Exception:
        return SESSION_MEMORY.get(session_id, [])


def save_memory(session_id: str, message):
    if session_id not in SESSION_MEMORY:
        SESSION_MEMORY[session_id] = []
    SESSION_MEMORY[session_id].append(message)

    try:
        _ensure_schema()
        history = get_memory(session_id)
        history.append(message)
        now = datetime.now(timezone.utc).isoformat()

        conn = _connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions (id, started_at, last_accessed, conversation_history)
            VALUES (%s, NOW(), NOW(), %s::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                last_accessed = NOW(),
                conversation_history = EXCLUDED.conversation_history
            """,
            (session_id, json.dumps(history, default=str)),
        )
        cursor.execute(
            """
            INSERT INTO audit_log (session_id, action, details)
            VALUES (%s, %s, %s::jsonb)
            """,
            (
                session_id,
                "agent_message",
                json.dumps({"timestamp": now, "message": message}, default=str),
            ),
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass


def clear_memory(session_id: str):
    SESSION_MEMORY.pop(session_id, None)

    try:
        _ensure_schema()
        conn = _connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass
