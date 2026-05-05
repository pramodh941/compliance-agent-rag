import requests
from ..registry import register_tool


@register_tool("compliance_scan")
def compliance_scan(input: dict):
    email_id = input.get("email_id")

    if not email_id:
        return {"error": "email_id is required"}

    try:
        res = requests.post(
            "http://api:8000/scan-email",
            params={"email_id": email_id},
            timeout=30
        )
        return res.json()
    except Exception as e:
        return {"error": str(e)}