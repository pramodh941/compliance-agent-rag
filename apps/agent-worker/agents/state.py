from typing import TypedDict, List, Dict, Any
from app.config import settings


class AgentState(TypedDict):

    user_input: str

    messages: List[Dict[str, str]]

    current_plan: str

    selected_tool: str

    tool_args: Dict[str, Any]

    tool_result: Dict[str, Any]

    observations: List[Dict[str, Any]]

    iteration_count: int

    max_iterations: settings.MAX_ITERATIONS

    final_response: Any

    should_continue: bool

    errors: List[str]

    conversation_history: list
    
    session_id: str