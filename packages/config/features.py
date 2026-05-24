"""
Feature toggles with graceful fallbacks.

Manages optional features:
- Reranking
- OCR
- Advanced PDF parsing
- Semantic chunking
- Table extraction
- Image extraction
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


logger = logging.getLogger(__name__)


def _env_bool(name: str) -> Optional[bool]:
    """Return a boolean env override, or None when the variable is unset."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return None

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False

    logger.warning(
        "%s has invalid boolean value %r; expected true/false. Ignoring override.",
        name,
        raw_value,
    )
    return None


def _profile_or_env(profile_enabled: bool, env_name: str) -> bool:
    """Use an explicit env var first, then the profile default."""
    override = _env_bool(env_name)
    return profile_enabled if override is None else override


def _env_bool_default(name: str, default: bool) -> bool:
    """Return an env boolean with a default when unset or invalid."""
    override = _env_bool(name)
    return default if override is None else override


class FeatureState(str, Enum):
    """Feature state."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    FALLBACK = "fallback"
    ERROR = "error"


@dataclass
class FeatureConfig:
    """Configuration for a feature."""
    
    name: str
    enabled: bool = True
    required: bool = False
    fallback_behavior: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    
    # Runtime state
    state: FeatureState = FeatureState.DISABLED
    error_message: Optional[str] = None
    
    def enable(self) -> None:
        """Enable the feature."""
        self.enabled = True
        self.state = FeatureState.ENABLED
        self.error_message = None
    
    def disable(self, reason: Optional[str] = None) -> None:
        """Disable the feature."""
        self.enabled = False
        self.state = FeatureState.DISABLED
        self.error_message = reason
    
    def set_fallback(self, reason: str) -> None:
        """Set feature to fallback state."""
        self.enabled = False
        self.state = FeatureState.FALLBACK
        self.error_message = reason
    
    def set_error(self, error: str) -> None:
        """Set feature to error state."""
        self.enabled = False
        self.state = FeatureState.ERROR
        self.error_message = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "required": self.required,
            "fallback_behavior": self.fallback_behavior,
            "dependencies": self.dependencies,
            "state": self.state.value,
            "error_message": self.error_message,
        }


class FeatureManager:
    """Manages feature toggles with graceful fallbacks."""
    
    def __init__(self):
        self.features: Dict[str, FeatureConfig] = {}
        self._initialize_features()
    
    def _initialize_features(self) -> None:
        """Initialize feature configurations."""
        self.features = {
            "reranker": FeatureConfig(
                name="reranker",
                enabled=_env_bool("ENABLE_RERANKING") or False,
                required=False,
                fallback_behavior="use_dense_retrieval_only",
                dependencies=["reranker_service"],
            ),
            "ocr": FeatureConfig(
                name="ocr",
                enabled=_env_bool("ENABLE_OCR") or False,
                required=False,
                fallback_behavior="skip_scanned_pages",
                dependencies=["tesseract"],
            ),
            "layout_parsing": FeatureConfig(
                name="layout_parsing",
                enabled=_env_bool("ENABLE_LAYOUT_PARSING") or False,
                required=False,
                fallback_behavior="use_simple_text_extraction",
                dependencies=["pdfplumber"],
            ),
            "table_extraction": FeatureConfig(
                name="table_extraction",
                enabled=_env_bool("ENABLE_TABLE_EXTRACTION") or False,
                required=False,
                fallback_behavior="skip_tables",
                dependencies=["pdfplumber"],
            ),
            "image_extraction": FeatureConfig(
                name="image_extraction",
                enabled=_env_bool("ENABLE_IMAGE_EXTRACTION") or False,
                required=False,
                fallback_behavior="skip_images",
                dependencies=["pdf2image"],
            ),
            "semantic_chunking": FeatureConfig(
                name="semantic_chunking",
                enabled=_env_bool("ENABLE_SEMANTIC_CHUNKING") or False,
                required=False,
                fallback_behavior="use_simple_chunking",
                dependencies=["sentence_transformers"],
            ),
            "hierarchy_detection": FeatureConfig(
                name="hierarchy_detection",
                enabled=_env_bool_default("ENABLE_HIERARCHY_DETECTION", True),
                required=False,
                fallback_behavior="flat_chunking",
                dependencies=[],
            ),
            "metadata_extraction": FeatureConfig(
                name="metadata_extraction",
                enabled=_env_bool_default("ENABLE_METADATA_EXTRACTION", True),
                required=False,
                fallback_behavior="minimal_metadata",
                dependencies=[],
            ),
        }
    
    def configure_from_profile(self, profile_config) -> None:
        """
        Configure features from deployment profile.
        
        Args:
            profile_config: ProfileConfig instance
        """
        self.features["reranker"].enabled = _profile_or_env(
            profile_config.enable_reranker,
            "ENABLE_RERANKING",
        )
        self.features["ocr"].enabled = _profile_or_env(profile_config.enable_ocr, "ENABLE_OCR")
        self.features["layout_parsing"].enabled = _profile_or_env(
            profile_config.enable_advanced_parsing,
            "ENABLE_LAYOUT_PARSING",
        )
        self.features["table_extraction"].enabled = _profile_or_env(
            profile_config.enable_advanced_parsing,
            "ENABLE_TABLE_EXTRACTION",
        )
        self.features["image_extraction"].enabled = _profile_or_env(
            profile_config.enable_advanced_parsing,
            "ENABLE_IMAGE_EXTRACTION",
        )
        self.features["semantic_chunking"].enabled = _profile_or_env(
            profile_config.enable_semantic_chunking,
            "ENABLE_SEMANTIC_CHUNKING",
        )
        
        # Update states
        for feature in self.features.values():
            if feature.enabled:
                feature.state = FeatureState.ENABLED
            else:
                feature.state = FeatureState.DISABLED
    
    def check_dependencies(self) -> Dict[str, Any]:
        """
        Check if feature dependencies are available.
        
        Returns:
            Dictionary with dependency status for each feature.
        """
        dependency_status = {}
        
        for feature_name, feature in self.features.items():
            if not feature.enabled:
                dependency_status[feature_name] = {"available": False, "reason": "disabled"}
                continue
            
            missing_deps = []
            for dep in feature.dependencies:
                if not self._check_dependency(dep):
                    missing_deps.append(dep)
            
            if missing_deps:
                dependency_status[feature_name] = {
                    "available": False,
                    "reason": "missing_dependencies",
                    "missing": missing_deps
                }
                # Set to fallback state
                feature.set_fallback(f"Missing dependencies: {missing_deps}")
            else:
                dependency_status[feature_name] = {"available": True, "reason": "ok"}
                feature.enable()
        
        return dependency_status
    
    def _check_dependency(self, dependency: str) -> bool:
        """Check if a dependency is available."""
        try:
            if dependency == "reranker_service":
                import requests
                base_url = os.getenv("RERANKER_URL", "http://compliance-reranker:7997")
                url = base_url if base_url.endswith("/health") else f"{base_url.rstrip('/')}/health"
                response = requests.get(url, timeout=2)
                return response.status_code == 200
            
            elif dependency == "tesseract":
                import pytesseract
                import subprocess
                result = subprocess.run(["tesseract", "--version"], capture_output=True, timeout=2)
                return result.returncode == 0
            
            elif dependency == "pdfplumber":
                import pdfplumber
                return True
            
            elif dependency == "pdf2image":
                import pdf2image
                return True
            
            elif dependency == "sentence_transformers":
                import sentence_transformers
                return True
            
            return False
        except ImportError:
            return False
        except Exception:
            return False
    
    def apply_fallbacks(self, model_capabilities: Dict[str, Any]) -> None:
        """
        Apply fallbacks based on model capabilities.
        
        Args:
            model_capabilities: Model capability check results
        """
        # Reranker fallback
        if not model_capabilities.get("reranker", {}).get("available", False):
            if self.features["reranker"].enabled:
                self.features["reranker"].set_fallback("Reranker not available")
                logger.warning("Reranker not available, using dense retrieval only")
        
        # OCR fallback
        if not model_capabilities.get("ocr", {}).get("available", False):
            if self.features["ocr"].enabled:
                self.features["ocr"].set_fallback("OCR not available")
                logger.warning("OCR not available, skipping scanned pages")
    
    def get_enabled_features(self) -> List[str]:
        """Get list of enabled features."""
        return [name for name, feature in self.features.items() if feature.enabled]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of feature states."""
        return {
            name: feature.to_dict()
            for name, feature in self.features.items()
        }
    
    def is_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        feature = self.features.get(feature_name)
        return feature.enabled if feature else False
    
    def get_fallback_behavior(self, feature_name: str) -> Optional[str]:
        """Get fallback behavior for a feature."""
        feature = self.features.get(feature_name)
        return feature.fallback_behavior if feature else None
