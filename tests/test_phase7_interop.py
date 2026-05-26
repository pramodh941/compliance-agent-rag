import sys
import unittest
from pathlib import Path
from unittest.mock import patch


AGENT_WORKER_PATH = Path(__file__).resolve().parents[1] / "apps" / "agent-worker"
sys.path.insert(0, str(AGENT_WORKER_PATH))

from agents.interop_metadata import build_adk_agent_metadata, build_agent_card
from agents.a2a_adapter import handle_jsonrpc
from agents.interop_skills import (
    INTEROP_SKILLS,
    WORKFLOW_DIRECTIVE_PREFIX,
    WorkflowPayloadError,
    build_workflow_prompt,
    list_interop_skills,
    workflow_to_mcp_plan,
)
from agents.router import route_intent


class Phase7InteropTests(unittest.TestCase):
    def test_agent_card_exposes_required_workflow_skills(self):
        card = build_agent_card()
        skill_ids = {skill["id"] for skill in card["skills"]}

        self.assertEqual(card["url"].split("/")[-1], "a2a")
        self.assertTrue(
            {
                "policy_lookup",
                "compliance_risk_analysis",
                "sec_regulation_explanation",
                "escalation_recommendation",
            }.issubset(skill_ids)
        )

    def test_adk_metadata_maps_skills_to_mcp_tools(self):
        metadata = build_adk_agent_metadata()
        tools = {tool["id"]: tool for tool in metadata["tools"]}

        self.assertEqual(metadata["runtime"]["type"], "langgraph")
        self.assertEqual(tools["policy_lookup"]["mcp_tools"], ["rag_search"])
        self.assertIn("analyze_text", tools["compliance_risk_analysis"]["mcp_tools"])
        self.assertIn("rag_search", tools["sec_regulation_explanation"]["mcp_tools"])

    def test_skill_metadata_is_json_serializable_shape(self):
        skills = list_interop_skills()

        self.assertEqual(len(skills), len(INTEROP_SKILLS))
        for skill in skills:
            self.assertIn("input_schema", skill)
            self.assertIn("output_schema", skill)
            self.assertIn("workflow", skill)

    def test_workflow_prompt_builds_router_directive(self):
        directive = build_workflow_prompt(
            "sec_regulation_explanation",
            {"query": "What is Reg FD?"},
        )

        self.assertTrue(directive.startswith(WORKFLOW_DIRECTIVE_PREFIX))
        self.assertEqual(
            route_intent(directive),
            {"tool": "rag_search", "arguments": {"query": "What is Reg FD?"}},
        )

    def test_policy_lookup_preserves_original_query_for_mcp(self):
        plan = workflow_to_mcp_plan("policy_lookup", {"query": "SEC marketing rule"})

        self.assertEqual(plan, {"tool": "rag_search", "arguments": {"query": "SEC marketing rule"}})

    def test_sec_regulation_explanation_preserves_original_query_for_mcp(self):
        plan = workflow_to_mcp_plan("sec_regulation_explanation", {"query": "SEC marketing rule"})

        self.assertEqual(plan, {"tool": "rag_search", "arguments": {"query": "SEC marketing rule"}})

    def test_escalation_recommendation_preserves_original_text_for_mcp(self):
        plan = workflow_to_mcp_plan(
            "escalation_recommendation",
            {"query": "confidential restricted disclosure"},
        )

        self.assertEqual(
            plan,
            {"tool": "analyze_text", "arguments": {"text": "confidential restricted disclosure"}},
        )

    def test_compliance_risk_analysis_routes_text_and_email_inputs(self):
        text_plan = workflow_to_mcp_plan("compliance_risk_analysis", {"text": "insider leak"})
        email_plan = workflow_to_mcp_plan("compliance_risk_analysis", {"email_id": "email-123"})

        self.assertEqual(text_plan, {"tool": "analyze_text", "arguments": {"text": "insider leak"}})
        self.assertEqual(email_plan, {"tool": "compliance_scan", "arguments": {"email_id": "email-123"}})

    def test_workflow_validation_rejects_missing_policy_query(self):
        with self.assertRaisesRegex(WorkflowPayloadError, "missing required"):
            workflow_to_mcp_plan("policy_lookup", {})

    def test_a2a_direct_workflow_input_reaches_runtime_as_directive(self):
        request = {
            "jsonrpc": "2.0",
            "id": "policy-test",
            "method": "message/send",
            "params": {
                "workflow": "policy_lookup",
                "input": {"query": "SEC marketing rule"},
                "session_id": "phase7-test",
            },
        }

        with patch("agents.a2a_adapter._invoke_langgraph_agent") as invoke:
            invoke.return_value = {
                "final_response": "ok",
                "observations": [],
                "errors": [],
            }
            response = handle_jsonrpc(request)

        prompt = invoke.call_args.args[0]
        self.assertEqual(invoke.call_args.kwargs["session_id"], "phase7-test")
        self.assertEqual(
            route_intent(prompt),
            {"tool": "rag_search", "arguments": {"query": "SEC marketing rule"}},
        )
        self.assertEqual(response["result"]["metadata"]["skill_id"], "policy_lookup")

    def test_a2a_rejects_invalid_workflow_payload(self):
        request = {
            "jsonrpc": "2.0",
            "id": "bad-policy-test",
            "method": "message/send",
            "params": {
                "workflow": "policy_lookup",
                "input": {},
            },
        }

        response = handle_jsonrpc(request)

        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("missing required", response["error"]["message"])

    def test_a2a_accepts_direct_workflow_envelope(self):
        request = {
            "workflow": "sec_regulation_explanation",
            "input": {"query": "SEC marketing rule"},
            "session_id": "direct-envelope",
        }

        with patch("agents.a2a_adapter._invoke_langgraph_agent") as invoke:
            invoke.return_value = {
                "final_response": "ok",
                "observations": [],
                "errors": [],
            }
            handle_jsonrpc(request)

        prompt = invoke.call_args.args[0]
        self.assertEqual(
            route_intent(prompt),
            {"tool": "rag_search", "arguments": {"query": "SEC marketing rule"}},
        )


if __name__ == "__main__":
    unittest.main()
