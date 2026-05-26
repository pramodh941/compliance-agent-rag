import logging
import uuid
from typing import Any, Dict, List

from agents.interop_skills import WorkflowPayloadError, build_workflow_prompt, get_skill


JSONRPC_VERSION = "2.0"
logger = logging.getLogger(__name__)


def _invoke_langgraph_agent(prompt: str, session_id: str) -> Dict[str, Any]:
    from agents.runtime import invoke_langgraph_agent

    return invoke_langgraph_agent(prompt, session_id=session_id)


def _jsonrpc_error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _extract_text(parts: List[Dict[str, Any]]) -> str:
    values = []
    for part in parts:
        if part.get("kind") == "text" and part.get("text"):
            values.append(part["text"])
        elif part.get("type") == "text" and part.get("text"):
            values.append(part["text"])
    return "\n".join(values).strip()


def _extract_payload(params: Dict[str, Any]) -> Dict[str, Any]:
    if "workflow" in params or "input" in params:
        workflow = params.get("workflow") or params.get("skill_id") or "policy_lookup"
        workflow_input = params.get("input", {})
        if not isinstance(workflow_input, dict):
            raise WorkflowPayloadError("input must be an object")
        payload = dict(workflow_input)
        payload["skill_id"] = workflow
        payload["session_id"] = params.get("session_id") or str(uuid.uuid4())
        return payload

    message = params.get("message", {})
    metadata = message.get("metadata", {}) or params.get("metadata", {}) or {}
    parts = message.get("parts", []) or params.get("parts", [])
    text = _extract_text(parts)

    payload = dict(metadata.get("payload", {}) or {})
    nested_input = metadata.get("input") or params.get("input")
    if isinstance(nested_input, dict):
        payload.update(nested_input)

    if text and "query" not in payload and "text" not in payload:
        payload["query"] = text
    if "skill_id" not in payload:
        payload["skill_id"] = (
            metadata.get("skill_id")
            or metadata.get("workflow")
            or params.get("skill_id")
            or params.get("workflow")
            or "policy_lookup"
        )
    payload["session_id"] = metadata.get("session_id") or params.get("session_id") or str(uuid.uuid4())
    return payload


def handle_jsonrpc(request: Dict[str, Any]) -> Dict[str, Any]:
    request_id = request.get("id")
    if request.get("jsonrpc") is None and ("workflow" in request or "input" in request):
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id or str(uuid.uuid4()),
            "method": "message/send",
            "params": request,
        }
        request_id = request["id"]

    if request.get("jsonrpc") != JSONRPC_VERSION:
        return _jsonrpc_error(request_id, -32600, "Invalid JSON-RPC version")

    method = request.get("method")
    if method not in {"message/send", "tasks/send"}:
        return _jsonrpc_error(request_id, -32601, f"Unsupported A2A method: {method}")

    params = request.get("params")
    if not isinstance(params, dict):
        return _jsonrpc_error(request_id, -32602, "params must be an object")

    try:
        payload = _extract_payload(params)
        skill_id = payload.pop("skill_id")
        session_id = payload.pop("session_id")
        get_skill(skill_id)
        prompt = build_workflow_prompt(skill_id, payload)
        logger.info(
            "A2A workflow transformed",
            extra={
                "workflow": skill_id,
                "session_id": session_id,
                "input_keys": sorted(payload.keys()),
            },
        )
    except KeyError as exc:
        logger.warning("A2A workflow rejected: %s", exc)
        return _jsonrpc_error(request_id, -32602, str(exc))
    except WorkflowPayloadError as exc:
        logger.warning("A2A workflow payload invalid: %s", exc)
        return _jsonrpc_error(request_id, -32602, str(exc))

    try:
        result = _invoke_langgraph_agent(prompt, session_id=session_id)
    except Exception as exc:
        logger.exception("A2A workflow execution failed", extra={"workflow": skill_id, "session_id": session_id})
        return _jsonrpc_error(request_id, -32000, f"workflow execution failed: {str(exc)}")

    response_text = result.get("final_response", result)

    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "result": {
            "kind": "message",
            "messageId": str(uuid.uuid4()),
            "role": "agent",
            "parts": [
                {
                    "kind": "data",
                    "data": {
                        "answer": response_text,
                        "observations": result.get("observations", []),
                        "errors": result.get("errors", []),
                    },
                }
            ],
            "metadata": {
                "session_id": session_id,
                "skill_id": skill_id,
                "runtime": "langgraph",
            },
        },
    }
