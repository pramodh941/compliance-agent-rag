from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from .registry import get_tool
from .tools import rag_tool as _
from .tools import compliance_tool as _
from fastapi import Depends, Header, HTTPException
import os
from .observability import tracer
import json

API_KEY = os.getenv("MCP_API_KEY")
if not API_KEY:
    raise RuntimeError("MCP_API_KEY not set")
app = FastAPI()


class ToolRequest(BaseModel):
    tool: str
    input: Dict[str, Any]

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/execute")
def execute_tool(req: ToolRequest, _: str = Depends(verify_api_key)):
    with tracer.start_as_current_span("execute_tool") as span:
        span.set_attribute("tool_name", req.tool)
        span.set_attribute("input.email_id", req.input.get("email_id", ""))
        tool_fn = get_tool(req.tool)

        if not tool_fn:
            return {"error": f"Tool '{req.tool}' not found"}

        result = tool_fn(req.input)
        span.set_attribute("tool_result", json.dumps(result)[:500])  # Log first 500 chars of result
        return result


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/tools")
def list_tools():
    return {
        "tools": [
            {
                "name": "rag_search",
                "description": "Answer questions using RAG",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "compliance_scan",
                "description": "Scan email for policy violations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string"}
                    },
                    "required": ["email_id"]
                }
            }
        ]
    }