import os

from dotenv import load_dotenv


load_dotenv()


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


settings = Settings()
