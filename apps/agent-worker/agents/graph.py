from langgraph.graph import StateGraph, END

from agents.state import AgentState

from agents.nodes import (
    planner_node,
    tool_executor_node,
    reflection_node,
)


builder = StateGraph(AgentState)

builder.add_node("planner", planner_node)

builder.add_node("tool_executor", tool_executor_node)

builder.add_node("reflection", reflection_node)

builder.set_entry_point("planner")

builder.add_edge("planner", "tool_executor")

builder.add_edge("tool_executor", "reflection")


def should_continue(state):

    if state["should_continue"]:
        return "planner"

    return END


builder.add_conditional_edges(
    "reflection",
    should_continue,
    {
        "planner": "planner",
        END: END,
    }
)

graph = builder.compile()