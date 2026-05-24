"""
Deployment profiles for different environments.

Defines configuration presets for:
- local-lite: Minimal resources, CPU-only, ~4GB RAM
- local-full: Full local development with optional GPU
- cloud-lite: Minimal cloud deployment
- cloud-production: Full production deployment
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class DeploymentProfile(str, Enum):
    """Available deployment profiles."""
    LOCAL_LITE = "local-lite"
    LOCAL_FULL = "local-full"
    CLOUD_LITE = "cloud-lite"
    CLOUD_PRODUCTION = "cloud-production"


@dataclass
class ProfileConfig:
    """Configuration for a deployment profile."""
    
    # Resource requirements
    min_ram_gb: int
    recommended_ram_gb: int
    cpu_cores: int
    gpu_required: bool = False
    gpu_optional: bool = False
    
    # Service availability
    enable_reranker: bool = False
    enable_ocr: bool = False
    enable_advanced_parsing: bool = False
    enable_semantic_chunking: bool = False
    
    # Model defaults
    llm_model: str = ""
    embedding_model: str = ""
    reranker_model: str = ""
    
    # Performance settings
    embedding_batch_size: int = 10
    max_concurrent_docs: int = 4
    dense_retrieval_limit: int = 5
    sparse_retrieval_k: int = 5
    rerank_top_k: int = 2
    
    # Timeout settings
    api_request_timeout: int = 180
    agent_run_timeout: int = 300
    planner_timeout: int = 180
    
    # Description
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for environment variable generation."""
        return {
            "min_ram_gb": self.min_ram_gb,
            "recommended_ram_gb": self.recommended_ram_gb,
            "cpu_cores": self.cpu_cores,
            "gpu_required": self.gpu_required,
            "gpu_optional": self.gpu_optional,
            "enable_reranker": self.enable_reranker,
            "enable_ocr": self.enable_ocr,
            "enable_advanced_parsing": self.enable_advanced_parsing,
            "enable_semantic_chunking": self.enable_semantic_chunking,
            "llm_model": self.llm_model,
            "embedding_model": self.embedding_model,
            "reranker_model": self.reranker_model,
            "embedding_batch_size": self.embedding_batch_size,
            "max_concurrent_docs": self.max_concurrent_docs,
            "dense_retrieval_limit": self.dense_retrieval_limit,
            "sparse_retrieval_k": self.sparse_retrieval_k,
            "rerank_top_k": self.rerank_top_k,
            "api_request_timeout": self.api_request_timeout,
            "agent_run_timeout": self.agent_run_timeout,
            "planner_timeout": self.planner_timeout,
        }


# Profile definitions
PROFILES: Dict[DeploymentProfile, ProfileConfig] = {
    DeploymentProfile.LOCAL_LITE: ProfileConfig(
        min_ram_gb=4,
        recommended_ram_gb=8,
        cpu_cores=2,
        gpu_required=False,
        gpu_optional=False,
        enable_reranker=False,
        enable_ocr=False,
        enable_advanced_parsing=False,
        enable_semantic_chunking=False,
        llm_model="gemma:2b",
        embedding_model="nomic-embed-text",
        reranker_model="",
        embedding_batch_size=5,
        max_concurrent_docs=2,
        dense_retrieval_limit=5,
        sparse_retrieval_k=5,
        rerank_top_k=2,
        api_request_timeout=180,
        agent_run_timeout=300,
        planner_timeout=180,
        description="Minimal local deployment for CPU-only systems with ~4GB RAM. "
                   "Uses lightweight models and disables optional features (reranker, OCR, advanced parsing)."
    ),
    
    DeploymentProfile.LOCAL_FULL: ProfileConfig(
        min_ram_gb=8,
        recommended_ram_gb=16,
        cpu_cores=4,
        gpu_required=False,
        gpu_optional=True,
        enable_reranker=True,
        enable_ocr=True,
        enable_advanced_parsing=True,
        enable_semantic_chunking=True,
        llm_model="llama3:8b",
        embedding_model="nomic-embed-text",
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        embedding_batch_size=10,
        max_concurrent_docs=4,
        dense_retrieval_limit=5,
        sparse_retrieval_k=5,
        rerank_top_k=2,
        api_request_timeout=180,
        agent_run_timeout=300,
        planner_timeout=180,
        description="Full local development environment with optional GPU support. "
                   "Enables all features including reranker, OCR, and advanced parsing."
    ),
    
    DeploymentProfile.CLOUD_LITE: ProfileConfig(
        min_ram_gb=4,
        recommended_ram_gb=8,
        cpu_cores=2,
        gpu_required=False,
        gpu_optional=False,
        enable_reranker=False,
        enable_ocr=False,
        enable_advanced_parsing=False,
        enable_semantic_chunking=False,
        llm_model="gemma:2b",
        embedding_model="nomic-embed-text",
        reranker_model="",
        embedding_batch_size=10,
        max_concurrent_docs=4,
        dense_retrieval_limit=5,
        sparse_retrieval_k=5,
        rerank_top_k=2,
        api_request_timeout=180,
        agent_run_timeout=300,
        planner_timeout=180,
        description="Minimal cloud deployment for cost-optimized scenarios. "
                   "Similar to local-lite but with cloud-optimized timeouts and batch sizes."
    ),
    
    DeploymentProfile.CLOUD_PRODUCTION: ProfileConfig(
        min_ram_gb=16,
        recommended_ram_gb=32,
        cpu_cores=8,
        gpu_required=False,
        gpu_optional=True,
        enable_reranker=True,
        enable_ocr=True,
        enable_advanced_parsing=True,
        enable_semantic_chunking=True,
        llm_model="llama3:8b",  # Can be overridden with cloud API
        embedding_model="nomic-embed-text",  # Can be overridden with cloud API
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        embedding_batch_size=20,
        max_concurrent_docs=8,
        dense_retrieval_limit=10,
        sparse_retrieval_k=10,
        rerank_top_k=5,
        api_request_timeout=300,
        agent_run_timeout=600,
        planner_timeout=300,
        description="Full production deployment with all features enabled. "
                   "Optimized for performance and reliability with cloud APIs."
    ),
}


def get_profile(profile_name: Optional[str] = None) -> ProfileConfig:
    """
    Get a deployment profile configuration.
    
    Args:
        profile_name: Profile name (e.g., "local-lite"). If None, reads from DEPLOYMENT_PROFILE env var.
    
    Returns:
        ProfileConfig for the specified profile.
    
    Raises:
        ValueError: If profile name is invalid.
    """
    if profile_name is None:
        profile_name = os.getenv("DEPLOYMENT_PROFILE", "local-lite")
    
    try:
        profile_enum = DeploymentProfile(profile_name)
    except ValueError:
        valid_profiles = [p.value for p in DeploymentProfile]
        raise ValueError(
            f"Invalid deployment profile: {profile_name}. "
            f"Valid profiles: {valid_profiles}"
        )
    
    return PROFILES[profile_enum]


def list_profiles() -> Dict[str, Dict[str, Any]]:
    """List all available deployment profiles with their configurations."""
    return {
        profile.value: config.to_dict()
        for profile, config in PROFILES.items()
    }
