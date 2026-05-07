def should_stop(state):
    """
    Decide whether the agent should terminate.
    """

    observations = state.get("observations", [])

    if not observations:
        return False

    # Stop if max iterations reached
    if state["iteration_count"] >= state["max_iterations"]:
        return True

    latest = observations[-1]

    result = latest.get("result")

    if not result:
        return False

    # If tool produced meaningful answer, stop
    if isinstance(result, dict):

        if result.get("answer"):
            return True

        analysis = result.get("analysis")

        if analysis:
            return True

    return False


def detect_repeated_tool_use(state):
    """
    Detect repeated tool calls.
    """

    observations = state.get("observations", [])

    if len(observations) < 2:
        return False

    last_tool = observations[-1]["tool"]
    prev_tool = observations[-2]["tool"]

    return last_tool == prev_tool