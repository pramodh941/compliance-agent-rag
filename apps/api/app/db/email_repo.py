import json

def get_email_by_id(email_id: str):
    with open("app/data/emails.json", "r") as f:
        emails = json.load(f)

    for e in emails:
        if e["id"] == email_id:
            return e

    return None