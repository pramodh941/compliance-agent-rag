import json
import requests


OLLAMA_URL = "http://ollama:11434/api/chat"


SYSTEM_PROMPT = """
You are an AI compliance agent planner.

Your task is to decide which MCP tool should be used.

Available tools:

1. ping
- health check tool

2. rag_search
- use for policy lookup
- use for compliance guidance
- use for document retrieval

Arguments:
{
  "query": "string"
}

3. analyze_text
- use for risk analysis
- use for suspicious text detection

Arguments:
{
  "text": "string"
}

4. compliance_scan
- use for scanning emails/documents

Arguments:
{
  "email_id": "string"
}

You MUST respond ONLY valid JSON.

Example:

{
  "tool": "rag_search",
  "arguments": {
    "query": "find insider trading policy"
  }
}
"""


def generate_plan(user_input: str, observations=None):

    observation_text = ""

    if observations:

        observation_text = f"""
    Previous observations:
    {json.dumps(observations, indent=2)}
    """

    user_prompt = f"""
    User request:
    {user_input}

    {observation_text}

    Choose the NEXT best tool.

    If enough information has been gathered,
    respond with:

    {{
    "tool": "final_answer",
    "arguments": {{
        "answer": "..."
    }}
    }}

    Return ONLY valid JSON.
    """

    payload = {
        "model": "gemma:2b",
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            }
        ],
        "stream": False,
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=120,
        )

        response.raise_for_status()

        data = response.json()

        raw_output = data["message"]["content"]

        print("RAW LLM OUTPUT:")
        print(raw_output)

        parsed = json.loads(raw_output)

        return parsed

    except Exception as e:

        return {
            "tool": "ping",
            "arguments": {},
            "error": str(e),
        }