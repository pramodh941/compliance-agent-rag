import json

from agents.interop_skills import WORKFLOW_DIRECTIVE_PREFIX


def route_intent(user_input: str):
    if user_input.startswith(WORKFLOW_DIRECTIVE_PREFIX):
        try:
            directive = json.loads(user_input[len(WORKFLOW_DIRECTIVE_PREFIX):])
            plan = directive.get("mcp_plan")
            if isinstance(plan, dict) and "tool" in plan and "arguments" in plan:
                return plan
        except (json.JSONDecodeError, TypeError):
            return None

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
