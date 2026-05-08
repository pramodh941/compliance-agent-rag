import requests

from app.config import settings

MCP_BASE_URL = settings.MCP_BASE_URL


def call_mcp_tool(tool_name: str, arguments: dict):

    url = f"{MCP_BASE_URL}/mcp/{tool_name}"

    try:
        response = requests.post(url, json=arguments, timeout=settings.MCP_TIMEOUT)

        response.raise_for_status()

        return response.json()

    except Exception as e:
        return {
            "error": str(e)
        }
