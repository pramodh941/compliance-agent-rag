import json
import re
import requests

from agents.schemas import PlannerResponse
from app.config import settings
from agents.router import route_intent


OLLAMA_URL = f"{settings.OLLAMA_BASE_URL}/api/chat"


SYSTEM_PROMPT = """
You are an AI compliance agent planner.

You MUST respond ONLY with valid JSON.

DO NOT explain your reasoning.

DO NOT use markdown.

DO NOT use code fences.

Available tools:

1. ping
- health check tool

Arguments:
{}

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

5. final_answer
- use when enough information exists

Arguments:
{
  "answer": "string"
}

Example response:

{
  "tool": "rag_search",
  "arguments": {
    "query": "find insider trading policy"
  }
}
"""


def extract_json(raw_text: str):

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)

    if not match:
        raise ValueError("No JSON object found")

    return match.group(0)


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

Choose the NEXT BEST TOOL.

If enough information exists,
return:

{{
  "tool": "final_answer",
  "arguments": {{
    "answer": "..."
  }}
}}

Return ONLY JSON.
"""
    routed = route_intent(user_input)

    if routed:
        print("ROUTER MATCHED:")
        print(routed)
        return routed

    payload = {
        "model": settings.PLANNER_MODEL,
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
            timeout=settings.PLANNER_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        raw_output = data["message"]["content"]

        print("RAW LLM OUTPUT:")
        print(raw_output)

        cleaned_json = extract_json(raw_output)

        parsed_dict = json.loads(cleaned_json)

        validated = PlannerResponse(**parsed_dict)

        return validated.model_dump()

    except Exception as e:

        print("PLANNER ERROR:")
        print(str(e))

        return {
            "tool": "ping",
            "arguments": {},
            "error": str(e),
        }