import json
import re


def extract_json(text: str):

    """
    Extract JSON object from messy LLM output.
    """

    # Remove markdown fences
    text = text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")

    # Try direct parse first
    try:
        return json.loads(text)
    except:
        pass

    # Try extracting first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:

        json_text = match.group(0)

        try:
            return json.loads(json_text)
        except:
            pass

    raise ValueError("Could not extract valid JSON")