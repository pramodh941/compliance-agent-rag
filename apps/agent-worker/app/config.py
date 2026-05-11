import os
import logging
import warnings

from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


class Settings:

    # =========================
    # OLLAMA
    # =========================

    OLLAMA_BASE_URL = os.getenv(
        "OLLAMA_BASE_URL",
        "http://ollama:11434"
    )

    PLANNER_MODEL = os.getenv(
        "PLANNER_MODEL",
        "gemma:2b"
    )

    PLANNER_TIMEOUT = int(
        os.getenv(
            "PLANNER_TIMEOUT",
            "180"
        )
    )

    # =========================
    # AGENT
    # =========================

    MAX_ITERATIONS = int(
        os.getenv(
            "MAX_ITERATIONS",
            "3"
        )
    )

    # =========================
    # MCP
    # =========================

    MCP_BASE_URL = os.getenv(
        "MCP_BASE_URL",
        "http://mcp-server:8001"
    )

    MCP_TIMEOUT = int(
        os.getenv(
            "MCP_TIMEOUT",
            "180"
        )
    )

    def validate(self):
        """Validate configuration and warn about invalid settings."""
        warnings_issued = []

        # Validate timeout ranges
        if self.PLANNER_TIMEOUT < 1 or self.PLANNER_TIMEOUT > 600:
            warnings_issued.append(
                f"PLANNER_TIMEOUT ({self.PLANNER_TIMEOUT}s) outside recommended range (1-600s)"
            )

        if self.MCP_TIMEOUT < 1 or self.MCP_TIMEOUT > 600:
            warnings_issued.append(
                f"MCP_TIMEOUT ({self.MCP_TIMEOUT}s) outside recommended range (1-600s)"
            )

        # Validate max iterations
        if self.MAX_ITERATIONS < 1 or self.MAX_ITERATIONS > 10:
            warnings_issued.append(
                f"MAX_ITERATIONS ({self.MAX_ITERATIONS}) outside recommended range (1-10)"
            )

        # Log warnings
        for warning in warnings_issued:
            logger.warning(f"Config validation: {warning}")

        return len(warnings_issued) == 0


settings = Settings()
settings.validate()
