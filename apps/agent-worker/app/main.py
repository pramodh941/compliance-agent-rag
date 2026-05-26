from fastapi import FastAPI
import signal
import sys
import logging

from pydantic import BaseModel

from agents.a2a_adapter import handle_jsonrpc
from agents.interop_metadata import build_adk_agent_metadata, build_agent_card
from agents.runtime import invoke_langgraph_agent

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


@app.get("/.well-known/agent.json")
def agent_json():
    return build_agent_card()


@app.get("/.well-known/agent-card.json")
def agent_card_json():
    return build_agent_card()


@app.get("/adk/agent")
def adk_agent_metadata():
    return build_adk_agent_metadata()


@app.post("/a2a")
def a2a_endpoint(request: dict):
    return handle_jsonrpc(request)


@app.post("/run")
def run_agent(request: RunRequest):
    result = invoke_langgraph_agent(request.input, session_id=request.session_id)

    return {
        "result": result
    }
