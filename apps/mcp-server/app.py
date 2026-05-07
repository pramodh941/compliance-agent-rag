from fastapi import FastAPI
from fastmcp import FastMCP
from tools import (
    extract_risk,
    compliance_scan_tool,
    rag_search_tool
)

app = FastAPI(title="Compliance MCP Server")

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