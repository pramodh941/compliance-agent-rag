import time
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

try:
    import requests
    REQUEST_EXCEPTIONS = (requests.exceptions.ConnectionError, requests.exceptions.Timeout)
except ImportError:
    requests = None
    REQUEST_EXCEPTIONS = ()

from config import settings

logger = logging.getLogger(__name__)


class ToolValidationError(ValueError):
    """Raised when an MCP tool request is malformed or unsafe to execute."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[..., Dict[str, Any]]
    description: str
    required_args: List[str]
    optional_args: List[str]
    timeout_seconds: int = settings.request_timeout_seconds

    @property
    def input_schema(self) -> Dict[str, Any]:
        properties = {
            arg: {"type": "string", "minLength": 1}
            for arg in [*self.required_args, *self.optional_args]
        }
        return {
            "type": "object",
            "properties": properties,
            "required": self.required_args,
            "additionalProperties": False,
        }


def retry_request(max_retries: int = settings.max_retries, base_delay: float = 0.5):
    """Simple retry decorator for MCP tool API calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except REQUEST_EXCEPTIONS as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        logger.error("MCP API call failed after retries", extra={"status": "error"})
                        raise
                    
                    delay = min(base_delay * (2 ** attempt), 2.0)
                    logger.warning(
                        "MCP API call failed, retrying",
                        extra={"status": "retry"},
                    )
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
    if requests is None:
        return {
            "query": query,
            "answer": "RAG search is unavailable because the requests package is not installed.",
            "sources": "",
            "status": "degraded",
            "error": "requests_not_installed",
        }

    # Call the real API endpoint
    response = requests.post(
        f"{settings.api_base_url}/qa",
        json={"query": query},
        timeout=settings.upstream_timeout_seconds
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
    if requests is None:
        return {
            "email_id": email_id,
            "analysis": {"error": "Compliance scan is unavailable because requests is not installed."},
            "context_used": "",
            "status": "degraded",
            "error": "requests_not_installed",
        }

    try:
        # Call the real API endpoint
        response = requests.post(
            f"{settings.api_base_url}/scan-email",
            json={"email_id": email_id},
            timeout=settings.upstream_timeout_seconds
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
        logger.exception("Compliance scan error", extra={"tool": "compliance_scan", "status": "error"})
        return {
            "email_id": email_id,
            "analysis": {"error": f"Error during compliance scan: {str(e)}"},
            "context_used": "",
            "status": "error",
            "error": str(e)
        }


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "ping": ToolSpec(
        name="ping",
        handler=lambda: {"status": "ok", "service": settings.service_name},
        description="Check MCP tool invocation connectivity.",
        required_args=[],
        optional_args=[],
    ),
    "analyze_text": ToolSpec(
        name="analyze_text",
        handler=extract_risk,
        description="Analyze free text for simple keyword-driven compliance risk.",
        required_args=["text"],
        optional_args=[],
    ),
    "compliance_scan": ToolSpec(
        name="compliance_scan",
        handler=compliance_scan_tool,
        description="Run compliance scanning for an email ID through the compliance API.",
        required_args=["email_id"],
        optional_args=[],
    ),
    "rag_search": ToolSpec(
        name="rag_search",
        handler=rag_search_tool,
        description="Search compliance knowledge through the RAG API.",
        required_args=["query"],
        optional_args=[],
    ),
}


def list_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
            "timeout_seconds": spec.timeout_seconds,
        }
        for spec in TOOL_REGISTRY.values()
    ]


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> ToolSpec:
    if tool_name not in TOOL_REGISTRY:
        raise ToolValidationError(f"Unknown tool: {tool_name}")

    if not isinstance(arguments, dict):
        raise ToolValidationError("Tool arguments must be a JSON object")

    spec = TOOL_REGISTRY[tool_name]
    missing = [arg for arg in spec.required_args if arg not in arguments]
    if missing:
        raise ToolValidationError(f"Missing required argument(s): {', '.join(missing)}")

    allowed = set(spec.required_args + spec.optional_args)
    unexpected = [arg for arg in arguments if arg not in allowed]
    if unexpected:
        raise ToolValidationError(f"Unexpected argument(s): {', '.join(unexpected)}")

    for key, value in arguments.items():
        if not isinstance(value, str):
            raise ToolValidationError(f"{key} must be a string")
        if not value.strip():
            raise ToolValidationError(f"{key} must not be empty")
        if len(value) > settings.max_text_chars:
            raise ToolValidationError(f"{key} exceeds maximum length of {settings.max_text_chars} characters")

    return spec


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    spec = validate_tool_arguments(tool_name, arguments)
    started = time.time()
    result = spec.handler(**arguments)
    duration_ms = round((time.time() - started) * 1000, 2)
    return {
        "tool": tool_name,
        "status": result.get("status", "success") if isinstance(result, dict) else "success",
        "duration_ms": duration_ms,
        "structured_content": result,
    }
