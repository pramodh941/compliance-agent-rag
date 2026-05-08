import psycopg2
from app.core.config import settings

def get_postgres_connection():
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname=settings.POSTGRES_DB
    )
    return conn


def initialize_schema():
    conn = get_postgres_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS emails (
            id VARCHAR(50) PRIMARY KEY,
            sender VARCHAR(255),
            recipient VARCHAR(255),
            subject TEXT,
            body TEXT,
            text TEXT,
            channel VARCHAR(100),
            timestamp TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails(sender)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_created ON emails(created_at)")

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            email_id VARCHAR(50),
            rule_type VARCHAR(100),
            message TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(email_id, rule_type, message)
        )
        """
    )

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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_last_accessed ON sessions(last_accessed)")

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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_session ON audit_log(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp)")

    conn.commit()
    cursor.close()
    conn.close()
