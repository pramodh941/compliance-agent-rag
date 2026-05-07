from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict):

    user_input: str

    messages: List[Dict[str, str]]

    current_plan: str

    selected_tool: str

    tool_args: Dict[str, Any]

    tool_result: Dict[str, Any]

    observations: List[Dict[str, Any]]

    iteration_count: int

    max_iterations: int

    final_response: Any

    should_continue: bool

    errors: List[str]