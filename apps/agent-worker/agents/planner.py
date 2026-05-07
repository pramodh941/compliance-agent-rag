import json
import requests
from agents.parser import extract_json


OLLAMA_URL = "http://ollama:11434/api/chat"


SYSTEM_PROMPT = """
You are an autonomous AI compliance agent.

Your role is to decide the NEXT BEST ACTION.

You operate in a reasoning loop:

plan
→ tool execution
→ observation
→ reflection
→ next decision

AVAILABLE TOOLS

1. ping
- health check tool
- use only for connectivity/system checks

Arguments:
{}

--------------------------------------------------

2. rag_search
- use for policy lookup
- use for compliance guidance
- use for document retrieval
- use when the user asks about rules, regulations, or policies

Arguments:
{
  "query": "string"
}

--------------------------------------------------

3. analyze_text
- use for risk analysis
- use for suspicious text detection
- use for analyzing raw text content

Arguments:
{
  "text": "string"
}

--------------------------------------------------

4. compliance_scan
- use for scanning emails/documents
- use for compliance risk detection

Arguments:
{
  "email_id": "string"
}

--------------------------------------------------

IMPORTANT BEHAVIOR RULES

1. DO NOT repeatedly call the same tool if the previous result was already useful

2. If previous observations already answer the user request,
respond with:

{
  "tool": "final_answer",
  "arguments": {
    "answer": "..."
  }
}

3. Prefer:
- rag_search → policy/rule questions
- compliance_scan → compliance investigation
- analyze_text → raw text analysis

4. Avoid unnecessary retries

5. Think step-by-step before selecting a tool

6. ONLY return valid JSON

7. NEVER explain your reasoning outside JSON

--------------------------------------------------

EXAMPLE

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
            timeout=300,
        )

        response.raise_for_status()

        data = response.json()

        raw_output = data["message"]["content"]

        print("RAW LLM OUTPUT:")
        print(raw_output)

        parsed = extract_json(raw_output)
        
        print("PARSED PLAN:")
        print(parsed)

        return parsed

    except Exception as e:

      print("PLANNER ERROR:")
      print(str(e))

      return {
          "tool": "final_answer",
          "arguments": {
              "answer": "Planner failed to generate valid tool selection."
          },
          "error": str(e),
      }