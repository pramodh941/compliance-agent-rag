import requests
import time

from app.core.config import settings
from app.core.logging import get_logger
from app.core.retry import retry_on_exception

OLLAMA_URL = settings.OLLAMA_BASE_URL
logger = get_logger(__name__)

@retry_on_exception(
    max_retries=2,
    base_delay=0.5,
    max_delay=2.0,
    exceptions=(requests.exceptions.ConnectionError, requests.exceptions.Timeout),
    operation_name="ollama_embedding"
)
def get_embedding(text: str):
    if not text or not text.strip():
        return None

    start_time = time.time()
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": [text[:settings.MAX_EMBEDDING_CHARS]]  # MUST be list
            },
            timeout=settings.API_REQUEST_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()

        if "embeddings" not in data or not data["embeddings"]:
            return None

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Embedding generation successful",
            extra={
                "operation": "ollama_embedding",
                "model": settings.EMBEDDING_MODEL,
                "text_length": len(text),
                "duration_ms": round(duration_ms, 2)
            }
        )
        return data["embeddings"][0]

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.warning(
            "Embedding generation failed",
            extra={
                "operation": "ollama_embedding",
                "model": settings.EMBEDDING_MODEL,
                "text_length": len(text),
                "duration_ms": round(duration_ms, 2),
                "error": str(e)
            }
        )
        return None

@retry_on_exception(
    max_retries=2,
    base_delay=0.5,
    max_delay=2.0,
    exceptions=(requests.exceptions.ConnectionError, requests.exceptions.Timeout),
    operation_name="ollama_generation"
)
def generate_response(prompt: str):
    start_time = time.time()
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": settings.PLANNER_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 60,     # limit output tokens
                "temperature": 0.2,     # more deterministic
                "top_p": 0.9,
                "num_ctx": 2048
            }
        },
        timeout=max(settings.API_REQUEST_TIMEOUT, 480)
    )
    response.raise_for_status()
    
    duration_ms = (time.time() - start_time) * 1000
    logger.info(
        "LLM generation successful",
        extra={
            "operation": "ollama_generation",
            "model": settings.PLANNER_MODEL,
            "prompt_length": len(prompt),
            "duration_ms": round(duration_ms, 2)
        }
    )
    return response.json()["response"]
