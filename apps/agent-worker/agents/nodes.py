from agents.mcp_client import call_mcp_tool
from agents.planner import generate_plan
from agents.validator import validate_plan
from agents.reflection import should_stop, detect_repeated_tool_use

def planner_node(state):

    plan = generate_plan(
        user_input=state["user_input"],
        observations=state.get("observations", []),
        conversation_history=state.get("conversation_history", []),
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

        state["final_response"] = state["tool_args"]

        state["should_continue"] = False

        return state

    tool = state["selected_tool"]

    args = state["tool_args"]

    result = call_mcp_tool(tool, args)

    normalized_result = result

    try:
        normalized_result = result["result"]["structured_content"]
    except (KeyError, TypeError) as e:
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

    tool_result = state.get("tool_result")

    selected_tool = state.get("selected_tool")

    observations = state.get("observations", [])

    # stop immediately for final answers
    if selected_tool == "final_answer":

        state["should_continue"] = False

        return state

    # stop if tool produced useful output
    if tool_result:

        state["final_response"] = tool_result

        state["should_continue"] = False

        return state

    # stop repeated tool loops
    if len(observations) >= 2:

        last_tool = observations[-1]["tool"]
        prev_tool = observations[-2]["tool"]

        if last_tool == prev_tool:

            state["final_response"] = {
                "message": "Stopping due to repeated tool usage."
            }

            state["should_continue"] = False

            return state

    state["should_continue"] = True

    return state