from fastapi import FastAPI

from pydantic import BaseModel

from agents.graph import graph


app = FastAPI()


class RunRequest(BaseModel):
    input: str


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/run")
def run_agent(request: RunRequest):

    initial_state = {
        "user_input": request.input,

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

    return {
        "result": result
    }