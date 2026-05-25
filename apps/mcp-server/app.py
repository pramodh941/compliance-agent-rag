import asyncio
import json
import signal
import sys
import time
import uuid
from typing import Any, Dict, Optional

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastmcp import FastMCP

from config import settings
from logging_utils import get_logger, setup_logging
from tools import (
    ToolValidationError,
    compliance_scan_tool,
    execute_tool,
    extract_risk,
    list_tools,
    rag_search_tool,
)


setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="Compliance MCP Server",
    version="1.0.0",
    description="HTTP-compatible MCP tool facade for compliance-agent-rag.",
)
mcp = FastMCP(settings.service_name)


def signal_handler(sig, frame):
    logger.info("Shutdown signal received, closing gracefully...", extra={"status": "shutdown"})
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def _extract_arguments(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if payload is None:
        return {}
    if "arguments" in payload and isinstance(payload.get("arguments"), dict):
        return payload["arguments"]
    return payload


async def verify_auth(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> None:
    if settings.auth_mode == "off":
        return

    token = x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    if not token or token != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing MCP credentials",
        )


@app.middleware("http")
async def request_context(request: Request, call_next):
    started = time.time()
    correlation_id = (
        request.headers.get("X-Correlation-ID")
        or request.headers.get("X-Request-ID")
        or str(uuid.uuid4())
    )
    request.state.correlation_id = correlation_id

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            payload_bytes = int(content_length)
        except ValueError:
            payload_bytes = 0
        if payload_bytes > settings.max_payload_bytes:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})

    logger.info(
        "MCP request started",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "client_host": request.client.host if request.client else None,
            "transport": "http",
        },
    )

    response = await call_next(request)
    duration_ms = round((time.time() - started) * 1000, 2)
    response.headers["X-Correlation-ID"] = correlation_id

    logger.info(
        "MCP request completed",
        extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "transport": "http",
        },
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@mcp.tool()
def ping():
    return {"status": "ok", "service": settings.service_name}


@mcp.tool()
def analyze_text(text: str):
    return extract_risk(text)


@mcp.tool()
def compliance_scan(email_id: str):
    return compliance_scan_tool(email_id)


@mcp.tool()
def rag_search(query: str):
    return rag_search_tool(query)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": settings.service_name,
        "transports": settings.allowed_transports,
        "tools_endpoint": "/mcp/tools",
    }


@app.get("/health")
def health():
    validation = settings.validate()
    return {
        "status": "healthy" if validation["valid"] else "degraded",
        "service": settings.service_name,
        "warnings": validation["warnings"],
    }


@app.get("/live")
def live():
    return {"status": "alive", "service": settings.service_name}


@app.get("/ready")
def ready(response: Response):
    validation = settings.validate()
    api_status = "unknown"
    try:
        upstream = requests.get(f"{settings.api_base_url}/health", timeout=5)
        api_status = "healthy" if upstream.ok else f"unhealthy:{upstream.status_code}"
    except requests.RequestException as exc:
        api_status = f"unreachable:{exc.__class__.__name__}"

    ready_status = validation["valid"] and api_status == "healthy"
    if not ready_status:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready_status else "not_ready",
        "service": settings.service_name,
        "api": api_status,
        "config": validation,
    }


@app.get("/mcp/tools", dependencies=[Depends(verify_auth)])
def tools_metadata():
    return {
        "service": settings.service_name,
        "transport": "http",
        "tools": list_tools(),
    }


@app.post("/mcp/{tool_name}", dependencies=[Depends(verify_auth)])
async def call_tool(tool_name: str, request: Request):
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON") from exc

    arguments = _extract_arguments(payload)
    logger.info(
        "MCP tool execution started",
        extra={"correlation_id": correlation_id, "tool": tool_name, "status": "started"},
    )

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(execute_tool, tool_name, arguments),
            timeout=settings.request_timeout_seconds,
        )
    except ToolValidationError as exc:
        logger.warning(
            "MCP tool request validation failed",
            extra={"correlation_id": correlation_id, "tool": tool_name, "status": "invalid"},
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except asyncio.TimeoutError as exc:
        logger.error(
            "MCP tool execution timed out",
            extra={"correlation_id": correlation_id, "tool": tool_name, "status": "timeout"},
        )
        raise HTTPException(status_code=504, detail="Tool execution timed out") from exc
    except Exception as exc:
        logger.exception(
            "MCP tool execution failed",
            extra={"correlation_id": correlation_id, "tool": tool_name, "status": "error"},
        )
        detail = str(exc) if settings.expose_errors else "Tool execution failed"
        raise HTTPException(status_code=502, detail=detail) from exc

    logger.info(
        "MCP tool execution completed",
        extra={
            "correlation_id": correlation_id,
            "tool": tool_name,
            "status": result.get("status"),
            "duration_ms": result.get("duration_ms"),
        },
    )
    return {"result": result}


@app.on_event("startup")
def startup():
    validation = settings.validate()
    for warning in validation["warnings"]:
        logger.warning("MCP configuration warning: %s", warning, extra={"status": "warning"})
    if not validation["valid"]:
        for error in validation["errors"]:
            logger.error("MCP configuration error: %s", error, extra={"status": "error"})
    logger.info("MCP server started", extra={"status": "started"})
