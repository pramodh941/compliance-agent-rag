"""
Centralized configuration for compliance-agent-rag.

Provides unified configuration management across all services with:
- Deployment profiles (local-lite, local-full, cloud-lite, cloud-production)
- Model configuration with capability detection
- Feature toggles with graceful fallbacks
- Startup diagnostics and validation

Usage:
    from packages.config import get_config
    
    config = get_config()
    config.validate()
    config.run_diagnostics()
    
    # Access configuration
    llm_model = config.models.llm
    embedding_model = config.models.embedding
    reranker_enabled = config.features.reranker.enabled
"""

from .core import Config, get_config, reset_config
from .profiles import DeploymentProfile, get_profile
from .models import ModelConfig, ModelProvider
from .features import FeatureConfig
from .diagnostics import Diagnostics

__all__ = [
    "Config",
    "get_config",
    "reset_config",
    "DeploymentProfile",
    "get_profile",
    "ModelConfig",
    "ModelProvider",
    "FeatureConfig",
    "Diagnostics",
]
