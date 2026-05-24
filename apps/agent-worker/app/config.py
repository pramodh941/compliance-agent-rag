"""
Agent Worker Configuration - Backward compatible wrapper around centralized config.

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

    # OLLAMA configuration
    OLLAMA_BASE_URL = _central_config.ollama_base_url
    PLANNER_MODEL = _central_config.model_manager.llm_model.name if _central_config.model_manager.llm_model else os.getenv("PLANNER_MODEL", "gemma:2b")
    PLANNER_TIMEOUT = int(os.getenv("PLANNER_TIMEOUT", str(_central_config.profile_config.planner_timeout)))

    # Agent configuration
    MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))

    # MCP configuration
    MCP_BASE_URL = _central_config.mcp_base_url
    MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", str(_central_config.profile_config.planner_timeout)))

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
