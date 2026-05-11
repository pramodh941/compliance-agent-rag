import os
import requests
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "180"))


def retry_request(max_retries: int = 2, base_delay: float = 0.5):
    """Simple retry decorator for MCP tool API calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error(f"MCP API call failed after {max_retries} retries: {e}")
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), 2.0)
                    logger.warning(f"MCP API call failed (attempt {attempt + 1}), retrying in {delay:.2f}s")
                    time.sleep(delay)
            
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


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


@retry_request(max_retries=2, base_delay=0.5)
def rag_search_tool(query: str):
    """
    Call the real RAG service via API /qa endpoint

    Args:
        query: The question to ask the RAG service

    Returns:
        dict: Response from the RAG service with answer and sources
    """
    # Call the real API endpoint
    response = requests.post(
        f"{API_BASE_URL}/qa",
        json={"query": query},
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


@retry_request(max_retries=2, base_delay=0.5)
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
            json={"email_id": email_id},
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
    except Exception as e:
        logger.error(f"[MCP] Compliance scan error: {e}")
        return {
            "email_id": email_id,
            "analysis": {"error": f"Error during compliance scan: {str(e)}"},
            "context_used": "",
            "status": "error",
            "error": str(e)
        }
