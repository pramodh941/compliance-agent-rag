from agents.tool_registry import TOOLS


def validate_plan(plan: dict):

    tool = plan.get("tool")

    arguments = plan.get("arguments", {})

    if tool not in TOOLS:

        return {
            "valid": False,
            "error": f"Unknown tool: {tool}"
        }

    required_args = TOOLS[tool]["required_args"]

    missing_args = []

    for arg in required_args:

        if arg not in arguments:
            missing_args.append(arg)

    if missing_args:

        return {
            "valid": False,
            "error": f"Missing arguments: {missing_args}"
        }

    return {
        "valid": True
    }