"""
Agent Service - Bridge between API and Agent Worker

This service handles communication with the agent-worker service,
managing agent execution, sessions, and response formatting.
"""

import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from app.core.config import settings
from app.core.logging import get_logger
from app.dependencies.postgres import get_postgres_connection, initialize_schema

load_dotenv()

# Configuration
AGENT_WORKER_URL = settings.AGENT_WORKER_URL

# Timeouts
AGENT_RUN_TIMEOUT = settings.AGENT_RUN_TIMEOUT
logger = get_logger(__name__)


class AgentServiceError(Exception):
    """Base exception for agent service errors"""
    pass


class AgentConnectionError(AgentServiceError):
    """Raised when agent-worker is unavailable"""
    pass


class AgentTimeoutError(AgentServiceError):
    """Raised when agent request times out"""
    pass


def run_agent(
    query: str,
    session_id: str = "default"
) -> Dict[str, Any]:
    """
    Execute the agent with a user query.
    
    The agent orchestrates tool calls (via MCP) to answer the question,
    including RAG searches, compliance scans, and analysis.
    
    Args:
        query: The user's question or request
        session_id: Session ID for conversation history
        
    Returns:
        dict: Agent response with result, observations, and status
        
    Raises:
        AgentConnectionError: If agent-worker is unavailable
        AgentTimeoutError: If agent request times out
    """
    
    try:
        logger.info("Running agent", extra={"session_id": session_id})
        
        # Call agent-worker endpoint
        response = requests.post(
            f"{AGENT_WORKER_URL}/run",
            json={
                "input": query,
                "session_id": session_id
            },
            timeout=AGENT_RUN_TIMEOUT
        )
        
        response.raise_for_status()
        
        data = response.json()
        
        # Extract result from agent response
        result = data.get("result", {})
        
        logger.info(
            "Agent completed",
            extra={"session_id": session_id, "status": result.get("should_continue", False)},
        )
        
        # Format response
        return {
            "status": "success",
            "session_id": session_id,
            "query": query,
            "result": {
                "answer": result.get("final_response", "No response generated"),
                "observations": result.get("observations", []),
                "iteration_count": result.get("iteration_count", 0),
                "errors": result.get("errors", [])
            }
        }
        
    except requests.exceptions.ConnectionError as e:
        logger.error("Agent-worker connection error: %s", e, extra={"session_id": session_id})
        raise AgentConnectionError(
            f"Cannot connect to agent-worker at {AGENT_WORKER_URL}. "
            "Is the service running? Error: {str(e)}"
        )
        
    except requests.exceptions.Timeout as e:
        logger.error("Agent-worker timeout: %s", e, extra={"session_id": session_id})
        raise AgentTimeoutError(
            f"Agent request timed out after {AGENT_RUN_TIMEOUT}s. "
            "The query may be too complex. Error: {str(e)}"
        )
        
    except requests.exceptions.HTTPError as e:
        logger.error("Agent-worker HTTP error: %s", e, extra={"session_id": session_id})
        
        # Try to get error details from agent
        try:
            error_data = e.response.json()
            error_msg = error_data.get("detail", str(e))
        except:
            error_msg = str(e)
            
        raise AgentServiceError(
            f"Agent returned error: {error_msg}"
        )
        
    except Exception as e:
        logger.exception("Unexpected agent execution error", extra={"session_id": session_id})
        raise AgentServiceError(
            f"Unexpected error during agent execution: {str(e)}"
        )


def get_session(session_id: str) -> Dict[str, Any]:
    """
    Get session information and conversation history.
    
    Note: Currently agent sessions are in-memory in agent-worker.
    This endpoint retrieves what's available in the current session.
    
    Args:
        session_id: The session ID to retrieve
        
    Returns:
        dict: Session information with conversation history
    """
    
    try:
        initialize_schema()
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, started_at, last_accessed, status, conversation_history, tool_calls
            FROM sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            return {
                "status": "not_found",
                "session_id": session_id,
                "messages": [],
            }

        return {
            "status": "success",
            "session_id": row[0],
            "user_id": row[1],
            "started_at": row[2],
            "last_accessed": row[3],
            "session_status": row[4],
            "messages": row[5] or [],
            "tool_calls": row[6] or [],
        }
        
    except Exception as e:
        logger.exception("Error retrieving session", extra={"session_id": session_id})
        raise AgentServiceError(
            f"Could not retrieve session {session_id}: {str(e)}"
        )


def list_sessions() -> Dict[str, Any]:
    """
    List all active sessions.
    
    Note: Currently sessions are in-memory in agent-worker.
    Future implementation will use persistent storage (Redis/Postgres).
    
    Returns:
        dict: List of active sessions (placeholder)
    """
    
    initialize_schema()
    conn = get_postgres_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, started_at, last_accessed, status, jsonb_array_length(conversation_history)
        FROM sessions
        ORDER BY last_accessed DESC
        LIMIT 100
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return {
        "status": "success",
        "sessions": [
            {
                "session_id": row[0],
                "started_at": row[1],
                "last_accessed": row[2],
                "session_status": row[3],
                "message_count": row[4],
            }
            for row in rows
        ],
    }


def health_check() -> Dict[str, Any]:
    """
    Check if agent-worker is available.
    
    Returns:
        dict: Health status
    """
    
    try:
        response = requests.get(
            f"{AGENT_WORKER_URL}/health",
            timeout=5
        )
        
        if response.status_code == 200:
            return {
                "status": "healthy",
                "agent_worker": "connected"
            }
        else:
            return {
                "status": "unhealthy",
                "agent_worker": "responding with error",
                "code": response.status_code
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "agent_worker": "disconnected",
            "error": str(e)
        }
