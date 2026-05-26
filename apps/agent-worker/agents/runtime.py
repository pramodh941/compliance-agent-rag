from typing import Any, Dict

from agents.graph import graph
from agents.memory import get_memory, save_memory


def invoke_langgraph_agent(query: str, session_id: str = "default") -> Dict[str, Any]:
    """Run the existing LangGraph agent without binding callers to FastAPI."""
    memory = get_memory(session_id)

    initial_state = {
        "user_input": query,
        "session_id": session_id,
        "conversation_history": memory,
        "messages": [],
        "current_plan": "",
        "selected_tool": "",
        "tool_args": {},
        "tool_result": "",
        "iteration_count": 0,
        "max_iterations": 3,
        "final_response": "",
        "should_continue": False,
        "errors": [],
        "observations": [],
    }

    result = graph.invoke(initial_state)

    save_memory(
        session_id,
        {
            "user": query,
            "response": result.get("final_response"),
        },
    )

    return result
