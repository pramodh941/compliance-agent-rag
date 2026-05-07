from typing import Dict, Any

from pydantic import BaseModel


class PlannerResponse(BaseModel):

    tool: str

    arguments: Dict[str, Any]