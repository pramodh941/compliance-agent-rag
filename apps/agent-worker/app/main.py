from fastapi import FastAPI

from pydantic import BaseModel

from agents.graph import graph
from agents.memory import get_memory, save_memory


app = FastAPI()


class RunRequest(BaseModel):
    input: str
    session_id: str = "default"


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/run")
def run_agent(request: RunRequest):

    memory = get_memory(request.session_id)

    initial_state = {

        "user_input": request.input,

        "session_id": request.session_id,

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
        request.session_id,
        {
            "user": request.input,
            "response": result.get("final_response"),
        }
    )

    return {
        "result": result
    }