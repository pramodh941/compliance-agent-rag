from fastapi import FastAPI
import signal
import sys
import logging

from pydantic import BaseModel

from agents.graph import graph
from agents.memory import get_memory, save_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Graceful shutdown handling
def signal_handler(sig, frame):
    logger.info("Shutdown signal received, closing gracefully...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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