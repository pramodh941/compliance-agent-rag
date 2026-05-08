import json
from app.services.rule_engine import evaluate_rules
from app.dependencies.postgres import get_postgres_connection
from app.db.email_repo import save_email, seed_emails_from_json

def ingest_emails():
    with open("app/data/emails.json", "r") as f:
        emails = json.load(f)

    seed_emails_from_json()

    conn = get_postgres_connection()
    cursor = conn.cursor()

    for email in emails:
        save_email(email)
        alerts = evaluate_rules(email)

        for alert in alerts:
            cursor.execute(
                """
                INSERT INTO alerts (email_id, rule_type, message)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (alert["email_id"], alert["rule_type"], alert["message"])
            )

    conn.commit()
    cursor.close()
    conn.close()

    return {"status": "ingestion_complete", "email_count": len(emails)}
