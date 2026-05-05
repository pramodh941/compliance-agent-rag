import re
import requests

# 🔹 Intent classifier
def classify_node(state):
    query = state["query"].lower()

    if "email" in query or "scan" in query:
        return {**state, "intent": "scan"}
    
    return {**state, "intent": "qa"}


# 🔹 Extract email id
def extract_email_node(state):
    match = re.search(r"e\d+", state["query"])
    email_id = match.group(0) if match else None

    return {**state, "email_id": email_id}


# 🔹 Call MCP - compliance scan
def compliance_node(state):
    email_id = state.get("email_id")

    res = requests.post(
        "http://mcp:8001/execute",
        json={
            "tool": "compliance_scan",
            "input": {"email_id": email_id}
        }
    )

    return {**state, "response": res.json()}


# 🔹 Call MCP - RAG QA
def rag_node(state):
    res = requests.post(
        "http://mcp:8001/execute",
        json={
            "tool": "rag_search",
            "input": {"query": state["query"]}
        }
    )

    return {**state, "response": res.json()}