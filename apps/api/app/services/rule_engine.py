RULES = {
    "MNPI": ["confidential", "inside information"],
    "Channel Change": ["whatsapp", "telegram", "move this offline"],
    "Gifts": ["gift", "voucher"]
}

def evaluate_rules(email):
    alerts = []

    text = email["text"].lower()

    for rule, keywords in RULES.items():
        for keyword in keywords:
            if keyword in text:
                alerts.append({
                    "email_id": email["id"],
                    "rule_type": rule,
                    "message": f"Keyword '{keyword}' detected"
                })
                break

    return alerts