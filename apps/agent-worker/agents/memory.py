SESSION_MEMORY = {}


def get_memory(session_id: str):

    return SESSION_MEMORY.get(session_id, [])


def save_memory(session_id: str, message):

    if session_id not in SESSION_MEMORY:
        SESSION_MEMORY[session_id] = []

    SESSION_MEMORY[session_id].append(message)


def clear_memory(session_id: str):

    SESSION_MEMORY.pop(session_id, None)