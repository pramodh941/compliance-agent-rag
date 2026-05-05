from typing import TypedDict, Optional, Dict


class AgentState(TypedDict):
    query: str
    intent: Optional[str]
    email_id: Optional[str]
    response: Optional[Dict]