from fastapi import APIRouter

from app.db.email_repo import list_emails
from app.services.rule_engine import evaluate_rules


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/compliance-summary")
def compliance_summary(limit: int = 100):
    emails = list_emails(limit=limit)
    alerts = []

    for email in emails:
        alerts.extend(evaluate_rules(email))

    by_rule = {}
    for alert in alerts:
        by_rule[alert["rule_type"]] = by_rule.get(alert["rule_type"], 0) + 1

    return {
        "status": "success",
        "email_count": len(emails),
        "alert_count": len(alerts),
        "alerts_by_rule": by_rule,
        "alerts": alerts,
    }
