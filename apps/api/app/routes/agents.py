"""
Agent Routes - Expose agent execution via API

Endpoints:
  POST /agents/run     - Execute agent with user query
  GET /agents/health   - Check agent-worker health
  GET /agents/sessions/{session_id} - Get session info (future)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, constr
from typing import Optional
from app.services.agent_service import (
    run_agent,
    get_session,
    list_sessions,
    health_check,
    AgentServiceError,
    AgentConnectionError,
    AgentTimeoutError
)

router = APIRouter(prefix="/agents", tags=["agents"])


class AgentRequest(BaseModel):
    """Request model for agent execution"""
    input: constr(max_length=2000) = Field(..., description="Agent input text (max 2000 characters)")
    session_id: Optional[constr(max_length=100)] = "default"


@router.post("/run")
def run_agent_endpoint(request: AgentRequest):
    """
    Execute the agent with a user query.
    
    The agent will:
    1. Parse the query
    2. Plan which tools to use (via LLM)
    3. Execute tools (RAG search, compliance scan, etc. via MCP)
    4. Reflect on results
    5. Return final answer
    
    Args:
        request: AgentRequest with input query and session_id
        
    Returns:
        dict: Agent response with answer, observations, and iteration count
        
    Raises:
        HTTPException: On connection, timeout, or agent errors
    """
    
    try:
        result = run_agent(
            query=request.input,
            session_id=request.session_id
        )
        return result
        
    except AgentConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Agent service unavailable: {str(e)}"
        )
        
    except AgentTimeoutError as e:
        raise HTTPException(
            status_code=504,
            detail=f"Agent request timeout: {str(e)}"
        )
        
    except AgentServiceError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@router.get("/health")
def agent_health():
    """
    Check if agent-worker service is running and healthy.
    
    Returns:
        dict: Health status of agent-worker
    """
    
    return health_check()


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str):
    """
    Get session information and conversation history.
    
    Note: Currently returns placeholder. Future implementation
    will use persistent storage (Redis/Postgres).
    
    Args:
        session_id: The session ID to retrieve
        
    Returns:
        dict: Session information
    """
    
    try:
        result = get_session(session_id)
        return result
        
    except AgentServiceError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve session: {str(e)}"
        )


@router.get("/sessions")
def list_sessions_endpoint():
    """
    List all active sessions.
    
    Note: Currently returns placeholder. Future implementation
    will use persistent storage.
    
    Returns:
        dict: List of active sessions
    """
    
    return list_sessions()
