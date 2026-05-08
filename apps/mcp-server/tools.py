import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "180"))


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


def rag_search_tool(query: str):
    """
    Call the real RAG service via API /qa endpoint
    
    Args:
        query: The question to ask the RAG service
        
    Returns:
        dict: Response from the RAG service with answer and sources
    """
    try:
        # Call the real API endpoint
        response = requests.post(
            f"{API_BASE_URL}/qa",
            params={"query": query},
            timeout=API_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Normalize response format
        return {
            "query": query,
            "answer": result.get("answer", {}).get("answer", "No answer found"),
            "sources": result.get("answer", {}).get("context_used", ""),
            "status": "success"
        }
    except requests.exceptions.ConnectionError as e:
        print(f"[MCP] API connection failed: {e}")
        return {
            "query": query,
            "answer": "API service unavailable",
            "sources": "",
            "status": "error",
            "error": str(e)
        }
    except requests.exceptions.Timeout as e:
        print(f"[MCP] API request timeout: {e}")
        return {
            "query": query,
            "answer": "API request timed out",
            "sources": "",
            "status": "error",
            "error": str(e)
        }
    except Exception as e:
        print(f"[MCP] RAG search error: {e}")
        return {
            "query": query,
            "answer": f"Error during RAG search: {str(e)}",
            "sources": "",
            "status": "error",
            "error": str(e)
        }


def compliance_scan_tool(email_id: str):
    """
    Call the real compliance scanning service via API /scan-email endpoint
    
    Args:
        email_id: The email ID to scan
        
    Returns:
        dict: Compliance scan results with violations and risk level
    """
    try:
        # Call the real API endpoint
        response = requests.post(
            f"{API_BASE_URL}/scan-email",
            params={"email_id": email_id},
            timeout=API_REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Normalize response format
        return {
            "email_id": email_id,
            "analysis": result.get("analysis", {}),
            "context_used": result.get("context_used", ""),
            "status": "success"
        }
    except requests.exceptions.ConnectionError as e:
        print(f"[MCP] API connection failed: {e}")
        return {
            "email_id": email_id,
            "analysis": {"error": "API service unavailable"},
            "context_used": "",
            "status": "error",
            "error": str(e)
        }
    except requests.exceptions.Timeout as e:
        print(f"[MCP] API request timeout: {e}")
        return {
            "email_id": email_id,
            "analysis": {"error": "API request timed out"},
            "context_used": "",
            "status": "error",
            "error": str(e)
        }
    except Exception as e:
        print(f"[MCP] Compliance scan error: {e}")
        return {
            "email_id": email_id,
            "analysis": {"error": f"Error during compliance scan: {str(e)}"},
            "context_used": "",
            "status": "error",
            "error": str(e)
        }
