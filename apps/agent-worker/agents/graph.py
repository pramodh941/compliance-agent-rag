from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes import (
    classify_node,
    extract_email_node,
    compliance_node,
    rag_node
)


def route(state):
    return state["intent"]


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("classify", classify_node)
    g.add_node("extract_email", extract_email_node)
    g.add_node("compliance", compliance_node)
    g.add_node("rag", rag_node)

    g.set_entry_point("classify")

    g.add_conditional_edges(
        "classify",
        route,
        {
            "scan": "extract_email",
            "qa": "rag"
        }
    )

    g.add_edge("extract_email", "compliance")
    g.add_edge("compliance", END)
    g.add_edge("rag", END)

    return g.compile()