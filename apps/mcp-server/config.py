import os
from dataclasses import dataclass, field
from typing import List

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False


load_dotenv()


def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 3600) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw_value!r}") from exc

    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}, got {value}")
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "*") -> List[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@dataclass(frozen=True)
class MCPSettings:
    service_name: str = os.getenv("MCP_SERVICE_NAME", "compliance-mcp")
    api_base_url: str = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
    port: int = _env_int("PORT", _env_int("MCP_PORT", 8001), minimum=1, maximum=65535)
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    environment: str = os.getenv("DEPLOYMENT_PROFILE", os.getenv("ENVIRONMENT", "local-lite"))

    request_timeout_seconds: int = _env_int("MCP_TOOL_TIMEOUT", _env_int("API_REQUEST_TIMEOUT", 180), maximum=600)
    upstream_timeout_seconds: int = _env_int("API_REQUEST_TIMEOUT", 180, maximum=600)
    max_payload_bytes: int = _env_int("MCP_MAX_PAYLOAD_BYTES", 65536, maximum=10_000_000)
    max_text_chars: int = _env_int("MCP_MAX_TEXT_CHARS", 20000, maximum=1_000_000)
    max_retries: int = _env_int("MCP_UPSTREAM_RETRIES", 2, minimum=0, maximum=5)

    auth_mode: str = os.getenv("MCP_AUTH_MODE", "off").lower()
    api_key: str = os.getenv("MCP_API_KEY", "")
    allowed_transports: List[str] = field(default_factory=lambda: _env_list("MCP_ALLOWED_TRANSPORTS", "http"))
    allowed_origins: List[str] = field(default_factory=lambda: _env_list("MCP_CORS_ORIGINS", "*"))
    expose_errors: bool = _env_bool("MCP_EXPOSE_ERROR_DETAILS", default=False)

    def validate(self) -> dict:
        errors = []
        warnings = []

        if not self.api_base_url.startswith(("http://", "https://")):
            errors.append("API_BASE_URL must be an HTTP(S) URL")

        if self.auth_mode not in {"off", "api-key"}:
            errors.append("MCP_AUTH_MODE must be one of: off, api-key")

        if self.auth_mode == "api-key" and not self.api_key:
            errors.append("MCP_API_KEY must be set when MCP_AUTH_MODE=api-key")

        if self.environment.startswith("cloud") and self.auth_mode == "off":
            warnings.append("MCP_AUTH_MODE=off is not recommended for cloud deployments")

        unsupported = [transport for transport in self.allowed_transports if transport not in {"http"}]
        if unsupported:
            warnings.append(
                "Only HTTP compatibility routes are enabled in this server; unsupported transports: "
                + ", ".join(unsupported)
            )

        return {"valid": not errors, "errors": errors, "warnings": warnings}


settings = MCPSettings()
