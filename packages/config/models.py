"""
Model configuration with capability detection.

Manages configuration for:
- LLM models (Ollama, OpenAI, etc.)
- Embedding models (Ollama, OpenAI, etc.)
- Reranker models (Infinity, local)
- OCR engines (Tesseract, cloud APIs)
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

# Optional imports - gracefully handle if not available
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Model provider types."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    COHERE = "cohere"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    
    name: str
    provider: ModelProvider
    enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_params: Dict[str, Any] = field(default_factory=dict)
    
    # Capability flags
    supports_embedding: bool = False
    supports_generation: bool = False
    supports_reranking: bool = False
    
    # Resource requirements
    min_ram_gb: float = 0.0
    requires_gpu: bool = False
    gpu_optional: bool = False
    
    # Fallback
    fallback_model: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "provider": self.provider.value,
            "enabled": self.enabled,
            "api_key": "***" if self.api_key else None,
            "base_url": self.base_url,
            "model_params": self.model_params,
            "supports_embedding": self.supports_embedding,
            "supports_generation": self.supports_generation,
            "supports_reranking": self.supports_reranking,
            "min_ram_gb": self.min_ram_gb,
            "requires_gpu": self.requires_gpu,
            "gpu_optional": self.gpu_optional,
            "fallback_model": self.fallback_model,
        }


# Model registry with capabilities
MODEL_REGISTRY: Dict[str, ModelConfig] = {
    # Ollama models
    "gemma:2b": ModelConfig(
        name="gemma:2b",
        provider=ModelProvider.OLLAMA,
        enabled=True,
        base_url="http://ollama:11434",
        supports_generation=True,
        supports_embedding=False,
        min_ram_gb=2.0,
        requires_gpu=False,
        gpu_optional=True,
        model_params={"num_ctx": 2048, "temperature": 0.2},
    ),
    "llama3:8b": ModelConfig(
        name="llama3:8b",
        provider=ModelProvider.OLLAMA,
        enabled=True,
        base_url="http://ollama:11434",
        supports_generation=True,
        supports_embedding=False,
        min_ram_gb=8.0,
        requires_gpu=False,
        gpu_optional=True,
        model_params={"num_ctx": 4096, "temperature": 0.2},
    ),
    "nomic-embed-text": ModelConfig(
        name="nomic-embed-text",
        provider=ModelProvider.OLLAMA,
        enabled=True,
        base_url="http://ollama:11434",
        supports_embedding=True,
        supports_generation=False,
        min_ram_gb=1.0,
        requires_gpu=False,
        gpu_optional=True,
    ),
    "mxbai-embed-large": ModelConfig(
        name="mxbai-embed-large",
        provider=ModelProvider.OLLAMA,
        enabled=True,
        base_url="http://ollama:11434",
        supports_embedding=True,
        supports_generation=False,
        min_ram_gb=2.0,
        requires_gpu=False,
        gpu_optional=True,
    ),
    
    # Reranker models
    "cross-encoder/ms-marco-MiniLM-L-6-v2": ModelConfig(
        name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        provider=ModelProvider.LOCAL,
        enabled=True,
        base_url="http://compliance-reranker:7997",
        supports_reranking=True,
        min_ram_gb=1.0,
        requires_gpu=False,
        gpu_optional=True,
    ),
    "cross-encoder/ms-marco-MiniLM-L-12-v2": ModelConfig(
        name="cross-encoder/ms-marco-MiniLM-L-12-v2",
        provider=ModelProvider.LOCAL,
        enabled=True,
        base_url="http://compliance-reranker:7997",
        supports_reranking=True,
        min_ram_gb=2.0,
        requires_gpu=False,
        gpu_optional=True,
    ),
    
    # OpenAI models (for cloud deployments)
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        enabled=False,
        supports_generation=True,
        supports_embedding=False,
        min_ram_gb=0.0,
        requires_gpu=False,
        model_params={"temperature": 0.2},
    ),
    "text-embedding-3-small": ModelConfig(
        name="text-embedding-3-small",
        provider=ModelProvider.OPENAI,
        enabled=False,
        supports_embedding=True,
        supports_generation=False,
        min_ram_gb=0.0,
        requires_gpu=False,
    ),
}


class ModelManager:
    """Manages model configuration and capability detection."""
    
    def __init__(self):
        self.llm_model: Optional[ModelConfig] = None
        self.embedding_model: Optional[ModelConfig] = None
        self.reranker_model: Optional[ModelConfig] = None
        self.ocr_engine: Optional[str] = None
        
    def configure(
        self,
        llm_model_name: str,
        embedding_model_name: str,
        reranker_model_name: Optional[str] = None,
        ocr_engine: Optional[str] = None,
    ) -> None:
        """
        Configure models from profile or environment.
        
        Args:
            llm_model_name: Name of LLM model
            embedding_model_name: Name of embedding model
            reranker_model_name: Name of reranker model (optional)
            ocr_engine: OCR engine to use (optional)
        """
        # Configure LLM
        self.llm_model = self._get_model_config(llm_model_name)
        if not self.llm_model:
            logger.warning(f"LLM model not found in registry: {llm_model_name}")
        
        # Configure embedding
        self.embedding_model = self._get_model_config(embedding_model_name)
        if not self.embedding_model:
            logger.warning(f"Embedding model not found in registry: {embedding_model_name}")
        
        # Configure reranker (optional)
        if reranker_model_name:
            self.reranker_model = self._get_model_config(reranker_model_name)
            if not self.reranker_model:
                logger.warning(f"Reranker model not found in registry: {reranker_model_name}")
        
        # Configure OCR
        self.ocr_engine = ocr_engine or os.getenv("OCR_ENGINE", "tesseract")
    
    def _get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get model configuration from registry."""
        if model_name in MODEL_REGISTRY:
            return MODEL_REGISTRY[model_name]
        
        # Try to create a basic config for unknown models
        provider = self._detect_provider(model_name)
        if provider:
            return ModelConfig(
                name=model_name,
                provider=provider,
                enabled=True,
                base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            )
        
        return None
    
    def _detect_provider(self, model_name: str) -> Optional[ModelProvider]:
        """Detect provider from model name."""
        if model_name.startswith("gpt-") or model_name.startswith("text-"):
            return ModelProvider.OPENAI
        if model_name.startswith("claude-"):
            return ModelProvider.ANTHROPIC
        if "/" in model_name and "cross-encoder" in model_name:
            return ModelProvider.LOCAL
        return ModelProvider.OLLAMA  # Default
    
    def check_capabilities(self) -> Dict[str, Any]:
        """
        Check if configured models are available and capable.
        
        Returns:
            Dictionary with capability status for each model.
        """
        capabilities = {
            "llm": self._check_model_capability(self.llm_model),
            "embedding": self._check_model_capability(self.embedding_model),
            "reranker": self._check_model_capability(self.reranker_model) if self.reranker_model else {"available": False, "reason": "not_configured"},
            "ocr": self._check_ocr_capability(),
        }
        return capabilities
    
    def _check_model_capability(self, model: Optional[ModelConfig]) -> Dict[str, Any]:
        """Check if a model is available and capable."""
        if not model:
            return {"available": False, "reason": "not_configured"}
        
        if not model.enabled:
            return {"available": False, "reason": "disabled"}
        
        # Check Ollama availability
        if model.provider == ModelProvider.OLLAMA:
            if not HAS_REQUESTS:
                logger.warning("requests library not available - cannot check Ollama availability")
                return {"available": False, "reason": "requests_not_available"}
            
            try:
                base_url = os.getenv("OLLAMA_BASE_URL", model.base_url or "http://ollama:11434")
                response = requests.get(f"{base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m["name"] for m in models]
                    if model.name in model_names:
                        return {"available": True, "reason": "ok"}
                    else:
                        return {"available": False, "reason": "model_not_pulled", "available_models": model_names}
                else:
                    return {"available": False, "reason": "ollama_unreachable"}
            except Exception as e:
                return {"available": False, "reason": f"connection_error: {str(e)}"}
        
        # Check local reranker
        if model.provider == ModelProvider.LOCAL and model.supports_reranking:
            if not HAS_REQUESTS:
                logger.warning("requests library not available - cannot check reranker availability")
                return {"available": False, "reason": "requests_not_available"}
            
            try:
                base_url = os.getenv("RERANKER_URL", model.base_url or "http://compliance-reranker:7997")
                response = requests.get(f"{base_url}/health", timeout=5)
                if response.status_code == 200:
                    return {"available": True, "reason": "ok"}
                else:
                    return {"available": False, "reason": "reranker_unhealthy"}
            except Exception as e:
                return {"available": False, "reason": f"connection_error: {str(e)}"}
        
        # Cloud providers (assume available if API key is set)
        if model.provider in [ModelProvider.OPENAI, ModelProvider.ANTHROPIC]:
            api_key = os.getenv(f"{model.provider.value.upper()}_API_KEY")
            if api_key:
                return {"available": True, "reason": "api_key_configured"}
            else:
                return {"available": False, "reason": "api_key_missing"}
        
        return {"available": False, "reason": "unknown_provider"}
    
    def _check_ocr_capability(self) -> Dict[str, Any]:
        """Check if OCR is available."""
        if not self.ocr_engine:
            return {"available": False, "reason": "not_configured"}
        
        if self.ocr_engine == "tesseract":
            try:
                import pytesseract
                # Try to run tesseract
                import subprocess
                result = subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return {"available": True, "reason": "ok", "engine": "tesseract"}
                else:
                    return {"available": False, "reason": "tesseract_not_installed"}
            except ImportError:
                return {"available": False, "reason": "pytesseract_not_installed"}
            except Exception as e:
                return {"available": False, "reason": f"error: {str(e)}"}
        
        return {"available": False, "reason": "unknown_engine"}
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of configured models."""
        return {
            "llm": self.llm_model.to_dict() if self.llm_model else None,
            "embedding": self.embedding_model.to_dict() if self.embedding_model else None,
            "reranker": self.reranker_model.to_dict() if self.reranker_model else None,
            "ocr": self.ocr_engine,
        }
