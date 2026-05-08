"""
JSON utilities for agent processing.

Handles robust JSON extraction from LLM outputs that may have formatting issues.
"""

import json
import re
from typing import Dict, Any


def extract_json(text: str) -> Dict[str, Any]:
    """
    Extract and parse JSON from potentially messy text.
    
    Handles various formatting issues that LLMs produce:
    - Markdown code fences (```json, ```)
    - Extra whitespace
    - Partial JSON objects
    
    Args:
        text: The text potentially containing JSON
        
    Returns:
        dict: The parsed JSON object
        
    Raises:
        ValueError: If no valid JSON can be extracted
    """
    
    # Remove markdown code fences
    text = text.strip()
    text = text.replace("```json", "")
    text = text.replace("```", "")
    text = text.strip()
    
    # Try direct parse first (fastest path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try extracting first JSON object using regex
    # This handles cases where there's text before/after JSON
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    
    if match:
        json_text = match.group(0)
        
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            # Try again with better handling of nested structures
            # Count braces to find complete JSON
            brace_count = 0
            start_idx = None
            
            for i, char in enumerate(text):
                if char == '{':
                    if start_idx is None:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if start_idx is not None and brace_count == 0:
                        json_text = text[start_idx:i+1]
                        try:
                            return json.loads(json_text)
                        except json.JSONDecodeError:
                            continue
    
    # If all else fails, raise error with helpful message
    raise ValueError(
        f"Could not extract valid JSON from text. "
        f"Attempted to find JSON object in: {text[:200]}..."
    )
