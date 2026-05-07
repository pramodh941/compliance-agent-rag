from typing import Dict, Any, Literal

from pydantic import BaseModel


class PlannerResponse(BaseModel):

    tool: Literal[
        "ping",
        "rag_search",
        "analyze_text",
        "compliance_scan",
        "final_answer",
    ]

    arguments: Dict[str, Any]