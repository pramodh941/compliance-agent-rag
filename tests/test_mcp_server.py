import sys
import unittest
from pathlib import Path


MCP_SERVER_PATH = Path(__file__).resolve().parents[1] / "apps" / "mcp-server"
sys.path.insert(0, str(MCP_SERVER_PATH))

from tools import ToolValidationError, execute_tool, list_tools, validate_tool_arguments


class MCPServerToolTests(unittest.TestCase):
    def test_tool_metadata_exposes_registered_tools(self):
        names = {tool["name"] for tool in list_tools()}

        self.assertTrue({"ping", "analyze_text", "compliance_scan", "rag_search"}.issubset(names))

    def test_ping_tool_executes_with_legacy_empty_payload(self):
        result = execute_tool("ping", {})

        self.assertEqual(result["tool"], "ping")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["structured_content"]["service"], "compliance-mcp")

    def test_tool_validation_rejects_unknown_tool(self):
        with self.assertRaisesRegex(ToolValidationError, "Unknown tool"):
            validate_tool_arguments("missing_tool", {})

    def test_tool_validation_rejects_missing_required_argument(self):
        with self.assertRaisesRegex(ToolValidationError, "Missing required"):
            validate_tool_arguments("rag_search", {})

    def test_tool_validation_rejects_unexpected_argument(self):
        with self.assertRaisesRegex(ToolValidationError, "Unexpected argument"):
            validate_tool_arguments("analyze_text", {"text": "ok", "extra": "nope"})

    def test_analyze_text_tool_uses_structured_result_shape(self):
        result = execute_tool("analyze_text", {"text": "confidential restricted memo"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["structured_content"]["classification"], "HIGH")


if __name__ == "__main__":
    unittest.main()
