import os
from typing import Any, Dict

from agents.interop_skills import INTEROP_SKILLS, JSON_OBJECT, TEXT, list_interop_skills


AGENT_NAME = "Compliance Agent RAG"
AGENT_VERSION = "1.0.0"


def public_base_url() -> str:
    return os.getenv("AGENT_PUBLIC_URL", os.getenv("AGENT_WORKER_URL", "http://localhost:8002")).rstrip("/")


def build_agent_card() -> Dict[str, Any]:
    base_url = public_base_url()
    return {
        "name": AGENT_NAME,
        "description": "Compliance RAG agent exposing policy lookup, risk analysis, SEC explanation, and escalation workflows.",
        "version": AGENT_VERSION,
        "url": f"{base_url}/a2a",
        "preferredTransport": "JSONRPC",
        "supportedInterfaces": [
            {
                "url": f"{base_url}/a2a",
                "protocolBinding": "JSONRPC",
                "protocolVersion": "2.0",
            }
        ],
        "provider": {
            "organization": "compliance-agent-rag",
            "url": base_url,
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
        },
        "defaultInputModes": [TEXT, JSON_OBJECT],
        "defaultOutputModes": [JSON_OBJECT],
        "skills": [skill.as_agent_skill() for skill in INTEROP_SKILLS],
        "securitySchemes": {},
        "security": [],
        "metadata": {
            "mcp_tools_endpoint": f"{os.getenv('MCP_BASE_URL', 'http://localhost:9000').rstrip('/')}/mcp/tools",
            "adk_metadata_endpoint": f"{base_url}/adk/agent",
            "a2a_agent_card_endpoint": f"{base_url}/.well-known/agent-card.json",
            "langgraph_preserved": True,
            "mcp_preserved": True,
        },
    }


def build_adk_agent_metadata() -> Dict[str, Any]:
    return {
        "name": AGENT_NAME,
        "version": AGENT_VERSION,
        "description": "Transport-agnostic ADK-compatible metadata for the existing LangGraph compliance agent.",
        "instruction": (
            "Use existing MCP-backed tools to answer compliance questions. Prefer RAG lookup for policy and SEC "
            "questions, analyze_text or compliance_scan for risk analysis, and explain escalation rationale clearly."
        ),
        "runtime": {
            "type": "langgraph",
            "entrypoint": "agents.runtime.invoke_langgraph_agent",
            "transport": "fastapi",
        },
        "tools": list_interop_skills(),
        "agent_card": build_agent_card(),
    }
