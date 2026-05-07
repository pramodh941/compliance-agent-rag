from agents.mcp_client import call_mcp_tool
from agents.planner import generate_plan
from agents.validator import validate_plan

def planner_node(state):

    plan = generate_plan(
        state["user_input"],
        state.get("observations", [])
    )

    validation = validate_plan(plan)

    if not validation["valid"]:

        return {
            **state,
            "current_plan": str(plan),
            "selected_tool": "ping",
            "tool_args": {},
            "errors": [validation["error"]],
        }

    tool = plan.get("tool")

    args = plan.get("arguments", {})

    should_continue = True

    final_response = ""

    if tool == "final_answer":

        should_continue = False

        final_response = args.get("answer")

    return {
        **state,
        "current_plan": str(plan),
        "selected_tool": tool,
        "tool_args": args,
        "should_continue": should_continue,
        "final_response": final_response,
    }


def tool_executor_node(state):
    if state["selected_tool"] == "final_answer":

        return state

    tool = state["selected_tool"]

    args = state["tool_args"]

    result = call_mcp_tool(tool, args)

    normalized_result = result

    try:
        normalized_result = result["result"]["structured_content"]
    except Exception:
        pass

    observations = state.get("observations", [])

    observations.append({
        "tool": tool,
        "arguments": args,
        "result": normalized_result,
    })

    return {
        **state,
        "tool_result": normalized_result,
        "observations": observations,
    }


def reflection_node(state):

    iteration = state["iteration_count"] + 1

    should_continue = state["should_continue"]

    if iteration >= state["max_iterations"]:
        should_continue = False

    return {
        **state,
        "iteration_count": iteration,
        "should_continue": should_continue,
    }