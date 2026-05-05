TOOLS = {}

def register_tool(name: str):
    def decorator(func):
        TOOLS[name] = func
        return func
    return decorator


def get_tool(name: str):
    return TOOLS.get(name)