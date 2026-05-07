def extract_risk(text: str):
    """
    Simple keyword-based risk analysis
    """
    keywords = ["confidential", "leak", "insider", "restricted"]

    score = sum(1 for k in keywords if k in text.lower())

    return {
        "risk_score": score,
        "classification": "HIGH" if score > 1 else "LOW"
    }


def compliance_scan_tool(email_id: str):
    """
    Mock compliance scan
    Replace later with DB/email lookup
    """

    sample_emails = {
        "e1": "This is confidential information",
        "e2": "Public announcement",
        "e3": "Insider trading discussion"
    }

    text = sample_emails.get(email_id, "")

    risk = extract_risk(text)

    return {
        "email_id": email_id,
        "content": text,
        "analysis": risk
    }


def rag_search_tool(query: str):
    """
    Mock RAG search
    Replace later with Qdrant/vector DB retrieval
    """

    return {
        "query": query,
        "answer": f"Mock RAG answer for: {query}"
    }