from dataclasses import dataclass
import json
from typing import Any, Dict, List


JSON_OBJECT = "application/json"
TEXT = "text/plain"
WORKFLOW_DIRECTIVE_PREFIX = "A2A_WORKFLOW:"


class WorkflowPayloadError(ValueError):
    """Raised when an A2A workflow payload cannot be safely routed."""


@dataclass(frozen=True)
class InteropSkill:
    id: str
    name: str
    description: str
    tags: List[str]
    examples: List[str]
    mcp_tools: List[str]
    workflow: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

    def as_agent_skill(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "examples": self.examples,
            "inputModes": [TEXT, JSON_OBJECT],
            "outputModes": [JSON_OBJECT],
        }

    def as_adk_skill(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "workflow": self.workflow,
            "mcp_tools": self.mcp_tools,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "examples": self.examples,
        }


TEXT_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "session_id": {"type": "string"},
    },
    "required": ["query"],
    "additionalProperties": False,
}

RISK_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string", "minLength": 1},
        "email_id": {"type": "string", "minLength": 1},
        "session_id": {"type": "string"},
    },
    "additionalProperties": False,
}

AGENT_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {},
        "observations": {"type": "array"},
        "errors": {"type": "array"},
    },
}

INTEROP_SKILLS: List[InteropSkill] = [
    InteropSkill(
        id="policy_lookup",
        name="Policy lookup",
        description="Find relevant internal policy and compliance knowledge through the existing RAG/MCP path.",
        tags=["policy", "rag", "lookup", "mcp"],
        examples=["Find the policy for restricted information handling."],
        mcp_tools=["rag_search"],
        workflow="policy_lookup",
        input_schema=TEXT_QUERY_SCHEMA,
        output_schema=AGENT_RESULT_SCHEMA,
    ),
    InteropSkill(
        id="compliance_risk_analysis",
        name="Compliance risk analysis",
        description="Analyze text or an email identifier for compliance risk using current MCP-backed tools.",
        tags=["risk", "compliance", "analysis", "mcp"],
        examples=["Analyze this message for insider trading risk."],
        mcp_tools=["analyze_text", "compliance_scan"],
        workflow="compliance_risk_analysis",
        input_schema=RISK_SCHEMA,
        output_schema=AGENT_RESULT_SCHEMA,
    ),
    InteropSkill(
        id="sec_regulation_explanation",
        name="SEC regulation explanation",
        description="Explain SEC regulatory concepts with supporting context from the repository RAG flow.",
        tags=["sec", "regulation", "explanation", "rag"],
        examples=["Explain SEC Reg FD in plain language."],
        mcp_tools=["rag_search"],
        workflow="sec_regulation_explanation",
        input_schema=TEXT_QUERY_SCHEMA,
        output_schema=AGENT_RESULT_SCHEMA,
    ),
    InteropSkill(
        id="escalation_recommendation",
        name="Escalation recommendation",
        description="Recommend whether a compliance item should be escalated and why.",
        tags=["escalation", "recommendation", "risk", "compliance"],
        examples=["Should this confidential disclosure be escalated?"],
        mcp_tools=["analyze_text", "rag_search"],
        workflow="escalation_recommendation",
        input_schema=TEXT_QUERY_SCHEMA,
        output_schema=AGENT_RESULT_SCHEMA,
    ),
]


def list_interop_skills() -> List[Dict[str, Any]]:
    return [skill.as_adk_skill() for skill in INTEROP_SKILLS]


def get_skill(skill_id: str) -> InteropSkill:
    for skill in INTEROP_SKILLS:
        if skill.id == skill_id:
            return skill
    raise KeyError(f"Unknown interoperability skill: {skill_id}")


def validate_workflow_payload(skill_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    skill = get_skill(skill_id)
    if not isinstance(payload, dict):
        raise WorkflowPayloadError("workflow input must be an object")

    allowed = set(skill.input_schema.get("properties", {}).keys()) | {"message"}
    unexpected = sorted(key for key in payload if key not in allowed)
    if unexpected:
        raise WorkflowPayloadError(f"unexpected workflow input field(s): {', '.join(unexpected)}")

    required = skill.input_schema.get("required", [])
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise WorkflowPayloadError(f"missing required workflow input field(s): {', '.join(missing)}")

    if skill.id == "compliance_risk_analysis" and not (payload.get("text") or payload.get("email_id")):
        raise WorkflowPayloadError("compliance_risk_analysis requires either text or email_id")

    validated = {}
    for key, value in payload.items():
        if value is None:
            continue
        if not isinstance(value, str):
            raise WorkflowPayloadError(f"{key} must be a string")
        stripped = value.strip()
        if not stripped:
            raise WorkflowPayloadError(f"{key} must not be empty")
        validated[key] = stripped

    return validated


def workflow_to_mcp_plan(skill_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    validated = validate_workflow_payload(skill_id, payload)
    skill = get_skill(skill_id)
    text = validated.get("query") or validated.get("text") or validated.get("message")
    email_id = validated.get("email_id")

    if skill.id == "compliance_risk_analysis" and email_id:
        return {"tool": "compliance_scan", "arguments": {"email_id": email_id}}
    if skill.id == "compliance_risk_analysis":
        return {"tool": "analyze_text", "arguments": {"text": text}}
    if skill.id in {"policy_lookup", "sec_regulation_explanation"}:
        return {"tool": "rag_search", "arguments": {"query": text}}
    if skill.id == "escalation_recommendation":
        return {"tool": "analyze_text", "arguments": {"text": text}}
    raise WorkflowPayloadError(f"unsupported workflow: {skill.id}")


def build_workflow_directive(skill_id: str, payload: Dict[str, Any]) -> str:
    plan = workflow_to_mcp_plan(skill_id, payload)
    directive = {
        "workflow": skill_id,
        "input": validate_workflow_payload(skill_id, payload),
        "mcp_plan": plan,
    }
    return f"{WORKFLOW_DIRECTIVE_PREFIX}{json.dumps(directive, sort_keys=True)}"


def build_workflow_prompt(skill_id: str, payload: Dict[str, Any]) -> str:
    return build_workflow_directive(skill_id, payload)
