"""
Core configuration module that ties together all configuration components.

Provides unified configuration management with:
- Deployment profile selection
- Model configuration
- Feature toggles
- Diagnostics and validation
- Security-first credential handling
"""

import logging
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from .profiles import get_profile, DeploymentProfile
from .models import ModelManager
from .features import FeatureManager
from .diagnostics import Diagnostics


logger = logging.getLogger(__name__)

SECRET_SENTINEL = "********"
_UNSET_MARKERS = {"", "changeme", "change-me", "your_secure_password_here"}


# Security: Detect production deployments to enforce stricter defaults
def _is_production_profile(profile_name: str) -> bool:
    """Check if profile is production-grade."""
    return profile_name in ["cloud-production", "cloud-lite"]


def _get_secure_default_password(profile_name: str) -> str:
    """
    Get secure default for postgres password.
    
    For production profiles, returns empty string to force explicit configuration.
    For development profiles, uses 'admin' as convenience default.
    
    NEVER use the returned empty string in production - must be explicitly set.
    """
    if _is_production_profile(profile_name):
        # Production: no default, must be explicitly provided
        return ""
    else:
        # Local development: use convenience default
        return "admin"


def _get_env_int(name: str, default: int) -> int:
    """Read an integer environment variable with an actionable error."""
    raw_value = os.getenv(name)
    if raw_value is None or raw_value == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw_value!r}") from exc


def _is_unresolved_secret(value: Optional[str]) -> bool:
    """Return True for unset, placeholder, or unexpanded shell-style secrets."""
    if value is None:
        return True

    normalized = value.strip()
    if normalized.lower() in _UNSET_MARKERS:
        return True

    return normalized.startswith("${") and normalized.endswith("}")


def mask_secret(value: Optional[str]) -> str:
    """Mask a secret value for logs, diagnostics, and summaries."""
    if not value:
        return ""
    return SECRET_SENTINEL


def mask_postgres_url(
    user: str,
    password: str,
    host: str,
    port: int,
    database: str,
) -> str:
    """Build a PostgreSQL URL with the password masked."""
    masked_password = mask_secret(password) or SECRET_SENTINEL
    return f"postgresql://{user}:{masked_password}@{host}:{port}/{database}"


@dataclass
class Config:
    """Centralized configuration for compliance-agent-rag."""
    
    # Profile
    profile_name: str = field(default_factory=lambda: os.getenv("DEPLOYMENT_PROFILE", "local-lite"))
    profile_config: Any = field(default=None)
    
    # Components
    model_manager: ModelManager = field(default_factory=ModelManager)
    feature_manager: FeatureManager = field(default_factory=FeatureManager)
    diagnostics: Diagnostics = field(default_factory=Diagnostics)
    
    # Database configuration
    postgres_host: str = field(default_factory=lambda: os.getenv("POSTGRES_HOST", "postgres"))
    postgres_port: int = field(default_factory=lambda: _get_env_int("POSTGRES_PORT", 5432))
    postgres_user: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "admin"))
    postgres_password: str = field(default="")  # Will be set in __post_init__
    postgres_db: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "compliance"))
    
    # Qdrant configuration
    qdrant_url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://qdrant:6333"))
    
    # Service URLs
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"))
    mcp_base_url: str = field(default_factory=lambda: os.getenv("MCP_BASE_URL", "http://mcp-server:8001"))
    agent_worker_url: str = field(default_factory=lambda: os.getenv("AGENT_WORKER_URL", "http://agent-worker:8002"))
    reranker_url: str = field(default_factory=lambda: os.getenv("RERANKER_URL", "http://compliance-reranker:7997"))
    
    # Ingestion configuration
    chunk_size: int = field(default_factory=lambda: _get_env_int("CHUNK_SIZE", 800))
    chunk_overlap: int = field(default_factory=lambda: _get_env_int("CHUNK_OVERLAP", 100))
    min_chunk_size: int = field(default_factory=lambda: _get_env_int("MIN_CHUNK_SIZE", 100))
    pdf_parser: str = field(default_factory=lambda: os.getenv("PDF_PARSER", "pypdf"))
    chunking_strategy: str = field(default_factory=lambda: os.getenv("CHUNKING_STRATEGY", "simple"))
    
    # Collection names
    policies_collection: str = field(default_factory=lambda: os.getenv("POLICIES_COLLECTION", "policies"))
    sec_docs_collection: str = field(default_factory=lambda: os.getenv("SEC_DOCS_COLLECTION", "sec_docs"))
    
    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    def __post_init__(self):
        """Initialize configuration after creation."""
        # Security: Set postgres password with profile-aware defaults
        if not self.postgres_password:
            default_pwd = _get_secure_default_password(self.profile_name)
            self.postgres_password = os.getenv("POSTGRES_PASSWORD", default_pwd)
        
        self.load_profile()
    
    def load_profile(self) -> None:
        """Load configuration from deployment profile."""
        logger.info(f"Loading deployment profile: {self.profile_name}")
        
        # Get profile configuration
        self.profile_config = get_profile(self.profile_name)
        
        # Configure models from profile
        self.model_manager.configure(
            llm_model_name=self._get_env_or_profile("LLM_MODEL", self.profile_config.llm_model),
            embedding_model_name=self._get_env_or_profile("EMBEDDING_MODEL", self.profile_config.embedding_model),
            reranker_model_name=self._get_env_or_profile("RERANKER_MODEL", self.profile_config.reranker_model),
            ocr_engine=os.getenv("OCR_ENGINE", "tesseract"),
        )
        
        # Configure features from profile
        self.feature_manager.configure_from_profile(self.profile_config)
        
        # Apply profile-specific settings
        # Note: Chunking parameters come from environment variables, not profile config
        self.chunk_size = self._get_env_or_profile_int("CHUNK_SIZE", 800)
        self.chunk_overlap = self._get_env_or_profile_int("CHUNK_OVERLAP", 100)
        
        logger.info(f"Profile loaded: {self.profile_name}")
    
    def _get_env_or_profile(self, env_var: str, profile_default: str) -> str:
        """Get value from environment or profile default."""
        return os.getenv(env_var, profile_default)
    
    def _get_env_or_profile_int(self, env_var: str, profile_default: int) -> int:
        """Get integer value from environment or profile default."""
        return _get_env_int(env_var, profile_default)
    
    @property
    def postgres_url(self) -> str:
        """
        Get masked PostgreSQL connection URL.
        
        SECURITY: Safe for summaries and logs because the password is masked.
        Use postgres_url_secure only for database connections.
        """
        return mask_postgres_url(
            self.postgres_user,
            self.postgres_password,
            self.postgres_host,
            self.postgres_port,
            self.postgres_db,
        )
    
    @property
    def postgres_url_secure(self) -> str:
        """
        Get full PostgreSQL connection URL with password.
        
        SECURITY WARNING: Use this only when absolutely necessary (e.g., for database connections).
        NEVER log or print this URL.
        """
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return f"postgresql://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Returns:
            Dictionary with validation results.
        """
        logger.info(f"Validating configuration for profile: {self.profile_name}")
        
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        
        is_production = _is_production_profile(self.profile_name)
        
        # Security: Validate PostgreSQL credentials
        if not self.postgres_user:
            validation_results["valid"] = False
            validation_results["errors"].append("POSTGRES_USER is not set")
        elif is_production and _is_unresolved_secret(self.postgres_user):
            validation_results["valid"] = False
            validation_results["errors"].append(
                "POSTGRES_USER is still a placeholder. Cloud profiles require explicit credentials."
            )
        elif is_production and os.getenv("POSTGRES_USER") is None:
            validation_results["valid"] = False
            validation_results["errors"].append(
                "POSTGRES_USER must be set explicitly for cloud profiles."
            )
        
        if _is_unresolved_secret(self.postgres_password):
            if is_production:
                validation_results["valid"] = False
                validation_results["errors"].append(
                    "POSTGRES_PASSWORD is not set or is still a placeholder. "
                    "Cloud profiles require explicit credentials from the environment or secrets manager."
                )
            else:
                validation_results["warnings"].append(
                    "POSTGRES_PASSWORD is not set. Using default for local development."
                )
        
        # Production security: warn on weak credentials
        if is_production:
            if self.postgres_user == "admin":
                validation_results["warnings"].append(
                    "POSTGRES_USER is 'admin' - use a dedicated database user for production"
                )
            if self.postgres_password == "admin":
                validation_results["valid"] = False
                validation_results["errors"].append(
                    "POSTGRES_PASSWORD is 'admin' - production deployments must use a strong password"
                )
        else:
            # Development: warn on default credentials
            if self.postgres_user == "admin" and self.postgres_password == "admin":
                validation_results["warnings"].append(
                    "Using default PostgreSQL credentials (admin/admin). "
                    "Set POSTGRES_USER and POSTGRES_PASSWORD environment variables for production."
                )
        
        # Validate profile
        try:
            get_profile(self.profile_name)
        except ValueError as e:
            validation_results["valid"] = False
            validation_results["errors"].append(str(e))

        # Validate ports and required endpoints
        if self.postgres_port < 1 or self.postgres_port > 65535:
            validation_results["valid"] = False
            validation_results["errors"].append(
                f"POSTGRES_PORT ({self.postgres_port}) must be between 1 and 65535"
            )

        for name, url in {
            "QDRANT_URL": self.qdrant_url,
            "OLLAMA_BASE_URL": self.ollama_base_url,
            "MCP_BASE_URL": self.mcp_base_url,
            "AGENT_WORKER_URL": self.agent_worker_url,
            "RERANKER_URL": self.reranker_url,
        }.items():
            if not url:
                validation_results["valid"] = False
                validation_results["errors"].append(f"{name} is not set")
            elif not (url.startswith("http://") or url.startswith("https://")):
                validation_results["warnings"].append(
                    f"{name} should be an HTTP(S) URL, got {url!r}"
                )
        
        # Validate chunking parameters
        if self.chunk_size < 100 or self.chunk_size > 2000:
            validation_results["warnings"].append(
                f"CHUNK_SIZE ({self.chunk_size}) outside recommended range (100-2000)"
            )
        
        if self.chunk_overlap < 0 or self.chunk_overlap > self.chunk_size:
            validation_results["warnings"].append(
                f"CHUNK_OVERLAP ({self.chunk_overlap}) invalid (should be 0 to CHUNK_SIZE)"
            )

        if self.min_chunk_size < 1 or self.min_chunk_size > self.chunk_size:
            validation_results["warnings"].append(
                f"MIN_CHUNK_SIZE ({self.min_chunk_size}) should be between 1 and CHUNK_SIZE"
            )
        
        # Validate PDF parser
        valid_parsers = ["pypdf", "pdfplumber", "pymupdf"]
        if self.pdf_parser not in valid_parsers:
            validation_results["warnings"].append(
                f"PDF_PARSER ({self.pdf_parser}) invalid. Must be one of: {valid_parsers}"
            )
        
        # Validate chunking strategy
        valid_strategies = ["simple", "semantic", "hierarchical", "recursive"]
        if self.chunking_strategy not in valid_strategies:
            validation_results["warnings"].append(
                f"CHUNKING_STRATEGY ({self.chunking_strategy}) invalid. Must be one of: {valid_strategies}"
            )
        
        # Log results
        for error in validation_results["errors"]:
            logger.error(f"Config validation error: {error}")
        for warning in validation_results["warnings"]:
            logger.warning(f"Config validation warning: {warning}")
        
        return validation_results
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """
        Run full diagnostics including capability checks.
        
        Returns:
            Dictionary with diagnostic results.
        """
        logger.info("Running diagnostics...")
        
        # Check model capabilities
        model_capabilities = self.model_manager.check_capabilities()
        
        # Check feature dependencies
        feature_dependencies = self.feature_manager.check_dependencies()
        
        # Apply fallbacks based on capabilities
        self.feature_manager.apply_fallbacks(model_capabilities)
        
        # Run startup checks
        diagnostic_results = self.diagnostics.run_startup_checks(
            profile_config=self.profile_config,
            model_capabilities=model_capabilities,
            feature_dependencies=feature_dependencies,
        )
        
        return diagnostic_results
    
    def check_service_health(self, services: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Check health of services.
        
        Args:
            services: Dictionary mapping service names to health check URLs.
                     If None, uses default services.
        
        Returns:
            Dictionary with service health status.
        """
        if services is None:
            services = {
                "qdrant": f"{self.qdrant_url}/",
                "ollama": f"{self.ollama_base_url}/api/tags",
                "reranker": f"{self.reranker_url}/health",
            }
        
        return self.diagnostics.check_service_health(services)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary."""
        return {
            "profile": {
                "name": self.profile_name,
                "description": self.profile_config.description if self.profile_config else "",
            },
            "models": self.model_manager.get_summary(),
            "features": self.feature_manager.get_summary(),
            "databases": {
                "postgres": {
                    "host": self.postgres_host,
                    "port": self.postgres_port,
                    "user": self.postgres_user,
                    "database": self.postgres_db,
                    "url": self.postgres_url,
                },
                "qdrant": {
                    "url": self.qdrant_url,
                },
            },
            "ingestion": {
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "pdf_parser": self.pdf_parser,
                "chunking_strategy": self.chunking_strategy,
            },
            "services": {
                "ollama": self.ollama_base_url,
                "mcp": self.mcp_base_url,
                "agent_worker": self.agent_worker_url,
                "reranker": self.reranker_url,
            },
        }
    
    def get_env_dict(self, include_secrets: bool = False) -> Dict[str, str]:
        """
        Get configuration as environment variable dictionary.
        
        Useful for generating .env files or passing to subprocesses.
        Secrets are masked by default; pass include_secrets=True only for
        trusted runtime handoff paths that require raw credentials.
        """
        env_dict = {
            "DEPLOYMENT_PROFILE": self.profile_name,
            "POSTGRES_HOST": self.postgres_host,
            "POSTGRES_PORT": str(self.postgres_port),
            "POSTGRES_USER": self.postgres_user,
            "POSTGRES_PASSWORD": self.postgres_password if include_secrets else mask_secret(self.postgres_password),
            "POSTGRES_DB": self.postgres_db,
            "QDRANT_URL": self.qdrant_url,
            "OLLAMA_BASE_URL": self.ollama_base_url,
            "MCP_BASE_URL": self.mcp_base_url,
            "AGENT_WORKER_URL": self.agent_worker_url,
            "RERANKER_URL": self.reranker_url,
            "CHUNK_SIZE": str(self.chunk_size),
            "CHUNK_OVERLAP": str(self.chunk_overlap),
            "PDF_PARSER": self.pdf_parser,
            "CHUNKING_STRATEGY": self.chunking_strategy,
            "POLICIES_COLLECTION": self.policies_collection,
            "SEC_DOCS_COLLECTION": self.sec_docs_collection,
            "LOG_LEVEL": self.log_level,
        }
        
        # Add model configurations
        if self.model_manager.llm_model:
            env_dict["LLM_MODEL"] = self.model_manager.llm_model.name
        if self.model_manager.embedding_model:
            env_dict["EMBEDDING_MODEL"] = self.model_manager.embedding_model.name
        if self.model_manager.reranker_model:
            env_dict["RERANKER_MODEL"] = self.model_manager.reranker_model.name
        
        # Add feature toggles
        env_dict["ENABLE_RERANKING"] = str(self.feature_manager.is_enabled("reranker")).lower()
        env_dict["ENABLE_OCR"] = str(self.feature_manager.is_enabled("ocr")).lower()
        env_dict["ENABLE_LAYOUT_PARSING"] = str(self.feature_manager.is_enabled("layout_parsing")).lower()
        env_dict["ENABLE_TABLE_EXTRACTION"] = str(self.feature_manager.is_enabled("table_extraction")).lower()
        env_dict["ENABLE_IMAGE_EXTRACTION"] = str(self.feature_manager.is_enabled("image_extraction")).lower()
        env_dict["ENABLE_SEMANTIC_CHUNKING"] = str(self.feature_manager.is_enabled("semantic_chunking")).lower()
        env_dict["ENABLE_HIERARCHY_DETECTION"] = str(self.feature_manager.is_enabled("hierarchy_detection")).lower()
        env_dict["ENABLE_METADATA_EXTRACTION"] = str(self.feature_manager.is_enabled("metadata_extraction")).lower()
        
        # Add profile-specific settings
        if self.profile_config:
            env_dict["API_REQUEST_TIMEOUT"] = str(self.profile_config.api_request_timeout)
            env_dict["AGENT_RUN_TIMEOUT"] = str(self.profile_config.agent_run_timeout)
            env_dict["PLANNER_TIMEOUT"] = str(self.profile_config.planner_timeout)
            env_dict["DENSE_RETRIEVAL_LIMIT"] = str(self.profile_config.dense_retrieval_limit)
            env_dict["SPARSE_RETRIEVAL_K"] = str(self.profile_config.sparse_retrieval_k)
            env_dict["RERANK_TOP_K"] = str(self.profile_config.rerank_top_k)
            env_dict["EMBEDDING_BATCH_SIZE"] = str(self.profile_config.embedding_batch_size)
            env_dict["MAX_CONCURRENT_DOCS"] = str(self.profile_config.max_concurrent_docs)
        
        return env_dict

    def get_safe_env_dict(self) -> Dict[str, str]:
        """Get environment values with secrets masked for debug output."""
        return self.get_env_dict(include_secrets=False)


# Global configuration instance
_config: Optional[Config] = None


def get_config(profile_name: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        profile_name: Deployment profile name. If None, uses DEPLOYMENT_PROFILE env var.
    
    Returns:
        Config instance.
    """
    global _config
    
    if _config is None:
        if profile_name:
            _config = Config(profile_name=profile_name)
        else:
            _config = Config()
    elif profile_name and _config.profile_name != profile_name:
        logger.info(
            "Switching configuration profile from %s to %s",
            _config.profile_name,
            profile_name,
        )
        _config = Config(profile_name=profile_name)
    
    return _config


def reset_config() -> None:
    """Reset the global configuration instance (useful for testing)."""
    global _config
    _config = None
