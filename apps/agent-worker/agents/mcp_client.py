import requests


MCP_BASE_URL = "http://mcp-server:8001"


def call_mcp_tool(tool_name: str, arguments: dict):

    url = f"{MCP_BASE_URL}/mcp/{tool_name}"

    try:
        response = requests.post(url, json=arguments, timeout=30)

        response.raise_for_status()

        return response.json()

    except Exception as e:
        return {
            "error": str(e)
        }