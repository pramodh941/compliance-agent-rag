import os
import logging
import warnings

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


class Settings:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "compliance")
    POSTGRES_URL = os.getenv(
        "POSTGRES_URL",
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
    )

    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    MCP_BASE_URL = os.getenv("MCP_BASE_URL", "http://mcp-server:8001")
    AGENT_WORKER_URL = os.getenv("AGENT_WORKER_URL", "http://agent-worker:8002")

    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    PLANNER_MODEL = os.getenv("PLANNER_MODEL", "gemma:2b")

    AGENT_RUN_TIMEOUT = int(os.getenv("AGENT_RUN_TIMEOUT", "300"))
    API_REQUEST_TIMEOUT = int(os.getenv("API_REQUEST_TIMEOUT", "180"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

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

        # Log warnings
        for warning in warnings_issued:
            logger.warning(f"Config validation: {warning}")

        return len(warnings_issued) == 0


settings = Settings()
settings.validate()
