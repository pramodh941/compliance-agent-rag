"""
Startup diagnostics and runtime capability checks.

Provides:
- System resource detection (optional - gracefully degrades without psutil)
- Service health checks
- Model availability checks
- Configuration validation
- Deployment profile compatibility checks
"""

import os
import logging
import platform
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

# Optional imports - gracefully handle if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.debug("psutil not available - system resource detection will be limited")


logger = logging.getLogger(__name__)


@dataclass
class SystemResources:
    """System resource information."""
    total_ram_gb: float
    available_ram_gb: float
    cpu_cores: int
    cpu_freq_mhz: float
    gpu_available: bool = False
    gpu_info: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_ram_gb": round(self.total_ram_gb, 2),
            "available_ram_gb": round(self.available_ram_gb, 2),
            "cpu_cores": self.cpu_cores,
            "cpu_freq_mhz": round(self.cpu_freq_mhz, 2),
            "gpu_available": self.gpu_available,
            "gpu_info": self.gpu_info,
        }


@dataclass
class ServiceHealth:
    """Service health status."""
    name: str
    healthy: bool
    url: str
    response_time_ms: float = 0.0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "healthy": self.healthy,
            "url": self.url,
            "response_time_ms": round(self.response_time_ms, 2),
            "error_message": self.error_message,
        }


class Diagnostics:
    """Startup diagnostics and capability checks."""
    
    def __init__(self):
        self.system_resources: Optional[SystemResources] = None
        self.service_health: Dict[str, ServiceHealth] = {}
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def _add_warning(self, warning: str) -> None:
        """Add a warning once to keep repeated checks readable."""
        if warning not in self.warnings:
            self.warnings.append(warning)
    
    def detect_system_resources(self) -> SystemResources:
        """
        Detect system resources.
        
        Gracefully handles case where psutil is not available.
        Returns minimal information if detection fails.
        """
        if not HAS_PSUTIL:
            logger.warning("psutil not available - system resource detection disabled")
            self._add_warning("psutil not installed - system resource detection unavailable")
            # Return minimal defaults
            self.system_resources = SystemResources(
                total_ram_gb=0.0,
                available_ram_gb=0.0,
                cpu_cores=0,
                cpu_freq_mhz=0.0,
                gpu_available=False,
                gpu_info=None,
            )
            return self.system_resources
        
        try:
            # RAM
            ram = psutil.virtual_memory()
            total_ram_gb = ram.total / (1024 ** 3)
            available_ram_gb = ram.available / (1024 ** 3)
            
            # CPU
            cpu_cores = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            cpu_freq_mhz = cpu_freq.current if cpu_freq else 0.0
            
            # GPU
            gpu_available, gpu_info = self._detect_gpu()
            
            self.system_resources = SystemResources(
                total_ram_gb=total_ram_gb,
                available_ram_gb=available_ram_gb,
                cpu_cores=cpu_cores,
                cpu_freq_mhz=cpu_freq_mhz,
                gpu_available=gpu_available,
                gpu_info=gpu_info,
            )
            
            logger.info(f"System resources detected: {self.system_resources.to_dict()}")
            return self.system_resources
            
        except Exception as e:
            logger.warning(f"Failed to detect system resources: {e}")
            self._add_warning(f"System resource detection failed: {e}")
            # Return minimal defaults on failure
            self.system_resources = SystemResources(
                total_ram_gb=0.0,
                available_ram_gb=0.0,
                cpu_cores=0,
                cpu_freq_mhz=0.0,
                gpu_available=False,
                gpu_info=None,
            )
            return self.system_resources
    
    def _detect_gpu(self) -> tuple[bool, Optional[str]]:
        """Detect GPU availability."""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                gpu_names = [torch.cuda.get_device_name(i) for i in range(gpu_count)]
                return True, ", ".join(gpu_names)
        except ImportError:
            pass
        
        try:
            import subprocess
            result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], 
                                  capture_output=True, timeout=2)
            if result.returncode == 0:
                gpu_names = result.stdout.decode().strip().split("\n")
                return True, ", ".join(gpu_names)
        except Exception:
            pass
        
        return False, None
    
    def check_service_health(self, services: Dict[str, str]) -> Dict[str, ServiceHealth]:
        """
        Check health of services.
        
        Args:
            services: Dictionary mapping service names to their health check URLs.
        
        Returns:
            Dictionary of service health status.
        """
        try:
            import requests
        except ImportError:
            logger.warning("requests library not available - service health checks disabled")
            self._add_warning("requests not installed - service health checks unavailable")
            return {}
        
        import time
        
        for service_name, url in services.items():
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5)
                response_time_ms = (time.time() - start_time) * 1000
                
                health = ServiceHealth(
                    name=service_name,
                    healthy=response.status_code == 200,
                    url=url,
                    response_time_ms=response_time_ms,
                )
                
                if not health.healthy:
                    self._add_warning(f"{service_name} health check failed with status {response.status_code}")
                
            except requests.exceptions.Timeout:
                health = ServiceHealth(
                    name=service_name,
                    healthy=False,
                    url=url,
                    error_message="timeout",
                )
                self._add_warning(f"{service_name} health check timed out")
            
            except Exception as e:
                health = ServiceHealth(
                    name=service_name,
                    healthy=False,
                    url=url,
                    error_message=str(e),
                )
                self._add_warning(f"{service_name} health check failed: {e}")
            
            self.service_health[service_name] = health
        
        return self.service_health
    
    def check_profile_compatibility(self, profile_config) -> Dict[str, Any]:
        """
        Check if system resources are compatible with deployment profile.
        
        Gracefully handles case where system resources couldn't be detected.
        
        Args:
            profile_config: ProfileConfig instance
        
        Returns:
            Dictionary with compatibility status.
        """
        if not self.system_resources:
            self.detect_system_resources()
        
        compatibility = {
            "compatible": True,
            "warnings": [],
            "errors": [],
        }
        
        # Check if system_resources is still None or all zeros (detection unavailable)
        if not self.system_resources or (self.system_resources.total_ram_gb == 0 and self.system_resources.cpu_cores == 0):
            compatibility["warnings"].append(
                "System resource detection unavailable - skipping compatibility checks"
            )
            return compatibility
        
        # Check RAM
        if self.system_resources.total_ram_gb > 0:
            if self.system_resources.total_ram_gb < profile_config.min_ram_gb:
                compatibility["compatible"] = False
                compatibility["errors"].append(
                    f"Insufficient RAM: {self.system_resources.total_ram_gb:.2f}GB available, "
                    f"{profile_config.min_ram_gb}GB required"
                )
            elif self.system_resources.total_ram_gb < profile_config.recommended_ram_gb:
                compatibility["warnings"].append(
                    f"RAM below recommended: {self.system_resources.total_ram_gb:.2f}GB available, "
                    f"{profile_config.recommended_ram_gb}GB recommended"
                )
        
        # Check CPU
        if self.system_resources.cpu_cores > 0:
            if self.system_resources.cpu_cores < profile_config.cpu_cores:
                compatibility["warnings"].append(
                    f"CPU cores below recommended: {self.system_resources.cpu_cores} available, "
                    f"{profile_config.cpu_cores} recommended"
                )
        
        # Check GPU
        if profile_config.gpu_required and not self.system_resources.gpu_available:
            compatibility["compatible"] = False
            compatibility["errors"].append(
                "GPU required but not available"
            )
        elif profile_config.gpu_optional and not self.system_resources.gpu_available:
            compatibility["warnings"].append(
                "GPU optional but not available (performance may be degraded)"
            )
        
        return compatibility
    
    def run_startup_checks(
        self,
        profile_config,
        model_capabilities: Dict[str, Any],
        feature_dependencies: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run all startup diagnostics.
        
        Args:
            profile_config: ProfileConfig instance
            model_capabilities: Model capability check results
            feature_dependencies: Feature dependency check results
        
        Returns:
            Dictionary with all diagnostic results.
        """
        logger.info("Running startup diagnostics...")
        
        # Detect system resources
        self.detect_system_resources()
        
        # Check profile compatibility
        profile_compatibility = self.check_profile_compatibility(profile_config)
        
        # Collect all results
        results = {
            "system_resources": self.system_resources.to_dict() if self.system_resources else {},
            "profile_compatibility": profile_compatibility,
            "model_capabilities": model_capabilities,
            "feature_dependencies": feature_dependencies,
            "service_health": {
                name: health.to_dict()
                for name, health in self.service_health.items()
            },
            "issues": self.issues,
            "warnings": self.warnings,
        }
        
        # Log summary
        logger.info(f"Startup diagnostics completed: "
                   f"{len(self.issues)} issues, {len(self.warnings)} warnings")
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get diagnostics summary."""
        return {
            "system_resources": self.system_resources.to_dict() if self.system_resources else {},
            "service_health": {
                name: health.to_dict()
                for name, health in self.service_health.items()
            },
            "issues": self.issues,
            "warnings": self.warnings,
        }
