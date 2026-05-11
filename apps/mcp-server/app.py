import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import signal
import sys
from fastmcp import FastMCP
from dotenv import load_dotenv
from tools import (
    extract_risk,
    compliance_scan_tool,
    rag_search_tool
)

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Compliance MCP Server")

# Graceful shutdown handling
def signal_handler(sig, frame):
    logger.info("Shutdown signal received, closing gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

mcp = FastMCP("compliance-mcp")


@mcp.tool()
def ping():
    return {
        "status": "ok",
        "service": "compliance-mcp"
    }


@mcp.tool()
def analyze_text(text: str):
    return extract_risk(text)


@mcp.tool()
def compliance_scan(email_id: str):
    return compliance_scan_tool(email_id)


@mcp.tool()
def rag_search(query: str):
    return rag_search_tool(query)


@app.post("/mcp/{tool_name}")
async def call_tool(tool_name: str, payload: dict = None):
    result = await mcp.call_tool(tool_name, payload or {})
    return {"result": result}


@app.get("/health")
def health():
    return {"status": "healthy"}