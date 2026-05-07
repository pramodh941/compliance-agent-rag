from agents.mcp_client import call_mcp_tool
from agents.planner import generate_plan
from agents.validator import validate_plan
from agents.reflection import should_stop, detect_repeated_tool_use

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

    # Stop if enough information gathered
    if should_stop(state):

        latest = state["observations"][-1]

        state["final_response"] = latest.get("result")

        state["should_continue"] = False

        return state

    # Stop if agent is looping
    if detect_repeated_tool_use(state):

        state["final_response"] = {
            "message": "Stopping due to repeated tool usage."
        }

        state["should_continue"] = False

        return state

    # Otherwise continue planning
    state["should_continue"] = True

    return state