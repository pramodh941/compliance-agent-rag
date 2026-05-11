import requests

from app.core.config import settings
from app.core.logging import get_logger
from app.core.retry import retry_on_exception

OLLAMA_URL = settings.OLLAMA_BASE_URL
logger = get_logger(__name__)

@retry_on_exception(
    max_retries=2,
    base_delay=0.5,
    max_delay=2.0,
    exceptions=(requests.exceptions.ConnectionError, requests.exceptions.Timeout)
)
def get_embedding(text: str):
    if not text or not text.strip():
        return None

    try:
        MAX_CHARS = 4000
        response = requests.post(
            f"{OLLAMA_URL}/api/embed",
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": [text[:MAX_CHARS]]  # MUST be list
            },
            timeout=settings.API_REQUEST_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()

        if "embeddings" not in data or not data["embeddings"]:
            return None

        return data["embeddings"][0]

    except Exception as e:
        logger.warning("Embedding generation failed: %s", e)
        return None

@retry_on_exception(
    max_retries=2,
    base_delay=0.5,
    max_delay=2.0,
    exceptions=(requests.exceptions.ConnectionError, requests.exceptions.Timeout)
)
def generate_response(prompt: str):
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": settings.PLANNER_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 60,     # 🔥 limit output tokens (BIG speed boost)
                "temperature": 0.2,     # more deterministic
                "top_p": 0.9,
                "num_ctx": 2048
            }
        },
        timeout=max(settings.API_REQUEST_TIMEOUT, 480)
    )
    response.raise_for_status()
    return response.json()["response"]
