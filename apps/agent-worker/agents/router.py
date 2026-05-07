def route_intent(user_input: str):

    text = user_input.lower()

    if any(word in text for word in [
        "policy",
        "guideline",
        "compliance policy",
        "insider trading"
    ]):
        return {
            "tool": "rag_search",
            "arguments": {
                "query": user_input
            }
        }

    if any(word in text for word in [
        "scan",
        "email",
        "document",
        "compliance risk"
    ]):
        return {
            "tool": "compliance_scan",
            "arguments": {
                "email_id": "test@example.com"
            }
        }

    if any(word in text for word in [
        "analyze",
        "suspicious",
        "risk"
    ]):
        return {
            "tool": "analyze_text",
            "arguments": {
                "text": user_input
            }
        }

    if text in ["hello", "hi", "hey"]:
        return {
            "tool": "final_answer",
            "arguments": {
                "answer": "Hello! How can I help with compliance operations today?"
            }
        }

    return None