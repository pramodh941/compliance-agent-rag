"""
API Configuration - Backward compatible wrapper around centralized config.

This module provides backward compatibility for existing code while
delegating to the new centralized configuration system.

New code should import from packages.config directly:
    from packages.config import get_config
    config = get_config()
"""

import os
import logging
import warnings

from dotenv import load_dotenv

# Import centralized configuration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../..'))
from packages.config import get_config

load_dotenv()
logger = logging.getLogger(__name__)

# Get centralized configuration
_central_config = get_config()


class Settings:
    """Backward compatible Settings class that wraps centralized config."""
    
    # Database configuration
    POSTGRES_HOST = _central_config.postgres_host
    POSTGRES_PORT = _central_config.postgres_port
    POSTGRES_USER = _central_config.postgres_user
    POSTGRES_PASSWORD = _central_config.postgres_password
    POSTGRES_DB = _central_config.postgres_db
    POSTGRES_URL = _central_config.postgres_url

    # Service URLs
    QDRANT_URL = _central_config.qdrant_url
    OLLAMA_BASE_URL = _central_config.ollama_base_url
    MCP_BASE_URL = _central_config.mcp_base_url
    AGENT_WORKER_URL = _central_config.agent_worker_url
    RERANKER_URL = _central_config.reranker_url

    # Model configuration (from centralized config)
    EMBEDDING_MODEL = _central_config.model_manager.embedding_model.name if _central_config.model_manager.embedding_model else os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    PLANNER_MODEL = _central_config.model_manager.llm_model.name if _central_config.model_manager.llm_model else os.getenv("PLANNER_MODEL", "gemma:2b")

    # Timeouts
    AGENT_RUN_TIMEOUT = int(os.getenv("AGENT_RUN_TIMEOUT", str(_central_config.profile_config.agent_run_timeout)))
    API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", str(_central_config.profile_config.api_request_timeout)))
    LOG_LEVEL = _central_config.log_level

    # RAG Retrieval Parameters (from profile config)
    DENSE_RETRIEVAL_LIMIT = _central_config.profile_config.dense_retrieval_limit
    SPARSE_RETRIEVAL_K = _central_config.profile_config.sparse_retrieval_k
    RERANK_TOP_K = _central_config.profile_config.rerank_top_k
    MAX_CONTEXT_LENGTH = int(os.getenv("MAX_CONTEXT_LENGTH", "400"))
    MAX_EMBEDDING_CHARS = int(os.getenv("MAX_EMBEDDING_CHARS", "4000"))
    
    # Feature toggles (from feature manager)
    ENABLE_RERANKING = _central_config.feature_manager.is_enabled("reranker")
    ENABLE_OCR = _central_config.feature_manager.is_enabled("ocr")
    ENABLE_LAYOUT_PARSING = _central_config.feature_manager.is_enabled("layout_parsing")
    ENABLE_SEMANTIC_CHUNKING = _central_config.feature_manager.is_enabled("semantic_chunking")

    def validate(self):
        """Validate configuration and warn about insecure defaults."""
        warnings_issued = []

        # Warn on default credentials
        if self.POSTGRES_USER == "admin" and self.POSTGRES_PASSWORD == "admin":
            warnings_issued.append(
                "Using default Postgres credentials (admin/admin). "
                "Set POSTGRES_USER and POSTGRES_PASSWORD environment variables for production."
            )

        # Validate timeout ranges
        if self.API_REQUEST_TIMEOUT < 1 or self.API_REQUEST_TIMEOUT > 600:
            warnings_issued.append(
                f"API_REQUEST_TIMEOUT ({self.API_REQUEST_TIMEOUT}s) outside recommended range (1-600s)"
            )

        if self.AGENT_RUN_TIMEOUT < 1 or self.AGENT_RUN_TIMEOUT > 900:
            warnings_issued.append(
                f"AGENT_RUN_TIMEOUT ({self.AGENT_RUN_TIMEOUT}s) outside recommended range (1-900s)"
            )

        # Validate port numbers
        if self.POSTGRES_PORT < 1 or self.POSTGRES_PORT > 65535:
            warnings_issued.append(f"Invalid POSTGRES_PORT: {self.POSTGRES_PORT}")

        # Validate RAG parameters
        if self.DENSE_RETRIEVAL_LIMIT < 1 or self.DENSE_RETRIEVAL_LIMIT > 20:
            warnings_issued.append(
                f"DENSE_RETRIEVAL_LIMIT ({self.DENSE_RETRIEVAL_LIMIT}) outside recommended range (1-20)"
            )

        if self.SPARSE_RETRIEVAL_K < 1 or self.SPARSE_RETRIEVAL_K > 20:
            warnings_issued.append(
                f"SPARSE_RETRIEVAL_K ({self.SPARSE_RETRIEVAL_K}) outside recommended range (1-20)"
            )

        if self.RERANK_TOP_K < 1 or self.RERANK_TOP_K > 10:
            warnings_issued.append(
                f"RERANK_TOP_K ({self.RERANK_TOP_K}) outside recommended range (1-10)"
            )

        # Log warnings
        for warning in warnings_issued:
            logger.warning(f"Config validation: {warning}")

        return len(warnings_issued) == 0


settings = Settings()
settings.validate()
