from app.services.rag_service import answer_question
from app.db.email_repo import get_email_by_id


def scan_email(email_id: str):
    email = get_email_by_id(email_id)

    if not email:
        return {"error": "Email not found"}

    print(f"[SCAN] Email ID: {email_id}")
    print(f"[SCAN] Email Text: {email['text'][:100]}")

    query = f"""
You are a financial compliance officer.

Analyze the following email for policy violations.

Email:
{email['text']}

Instructions:
- Detect potential violations even if not explicit
- Pay special attention to:
  - Insider trading (MNPI)
  - Market manipulation
  - Front-running
  - Unauthorized information sharing
  - Use of unapproved communication channels
- Be strict and conservative in judgement

Return ONLY JSON:

{{
  "violations": [
    {{
      "policy": "<policy name>",
      "reason": "<why this violates>"
    }}
  ],
  "risk_level": "LOW | MEDIUM | HIGH",
  "explanation": "<clear explanation>"
}}
"""

    rag_result = answer_question(query)

    return {
        "email_id": email_id,
        "analysis": rag_result["answer"],
        "context_used": rag_result["context_used"]
    }