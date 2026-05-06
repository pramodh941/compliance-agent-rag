from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any
from .registry import get_tool
from .tools import rag_tool as _
from .tools import compliance_tool as _

app = FastAPI()


class ToolRequest(BaseModel):
    tool: str
    input: Dict[str, Any]


@app.post("/execute")
def execute_tool(req: ToolRequest):
    tool_fn = get_tool(req.tool)

    if not tool_fn:
        return {"error": f"Tool '{req.tool}' not found"}

    result = tool_fn(req.input)
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