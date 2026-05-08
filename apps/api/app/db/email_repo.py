import json
from pathlib import Path

from app.dependencies.postgres import get_postgres_connection, initialize_schema


SEED_PATH = Path("app/data/emails.json")


def _row_to_email(row):
    if not row:
        return None
    return {
        "id": row[0],
        "sender": row[1],
        "recipient": row[2],
        "subject": row[3],
        "body": row[4],
        "text": row[5] or row[4] or "",
        "channel": row[6],
        "timestamp": row[7],
        "created_at": row[8],
    }


def save_email(email: dict):
    initialize_schema()
    conn = get_postgres_connection()
    cursor = conn.cursor()
    text = email.get("text") or email.get("body") or ""

    cursor.execute(
        """
        INSERT INTO emails (id, sender, recipient, subject, body, text, channel, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            sender = EXCLUDED.sender,
            recipient = EXCLUDED.recipient,
            subject = EXCLUDED.subject,
            body = EXCLUDED.body,
            text = EXCLUDED.text,
            channel = EXCLUDED.channel,
            timestamp = EXCLUDED.timestamp
        """,
        (
            email["id"],
            email.get("sender"),
            email.get("recipient"),
            email.get("subject"),
            email.get("body", text),
            text,
            email.get("channel"),
            email.get("timestamp"),
        ),
    )
    conn.commit()
    cursor.close()
    conn.close()


def seed_emails_from_json():
    if not SEED_PATH.exists():
        return 0

    with SEED_PATH.open("r", encoding="utf-8") as f:
        emails = json.load(f)

    for email in emails:
        save_email(email)

    return len(emails)


def get_email_by_id(email_id: str):
    initialize_schema()
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, sender, recipient, subject, body, text, channel, timestamp, created_at
        FROM emails
        WHERE id = %s
        """,
        (email_id,),
    )
    email = _row_to_email(cursor.fetchone())
    cursor.close()
    conn.close()

    if email:
        return email

    seed_emails_from_json()
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, sender, recipient, subject, body, text, channel, timestamp, created_at
        FROM emails
        WHERE id = %s
        """,
        (email_id,),
    )
    email = _row_to_email(cursor.fetchone())
    cursor.close()
    conn.close()
    return email


def list_emails(limit: int = 100):
    initialize_schema()
    seed_emails_from_json()
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, sender, recipient, subject, body, text, channel, timestamp, created_at
        FROM emails
        ORDER BY id
        LIMIT %s
        """,
        (limit,),
    )
    emails = [_row_to_email(row) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return emails


def delete_email(email_id: str):
    initialize_schema()
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM emails WHERE id = %s", (email_id,))
    deleted = cursor.rowcount
    conn.commit()
    cursor.close()
    conn.close()
    return deleted > 0
