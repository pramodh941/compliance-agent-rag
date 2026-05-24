#!/usr/bin/env python3
"""
Startup validation script for compliance-agent-rag.

This script validates configuration, checks system resources, and verifies
optional runtime capabilities before starting the application. Optional checks
warn and continue; only critical configuration errors produce a non-zero exit.

Usage:
    python scripts/validate_startup.py [--profile PROFILE] [--verbose] [--json]
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from packages.config import get_config
except ImportError as exc:
    print(f"[ERROR] Failed to import configuration module: {exc}")
    print("        Run from the project root or set PYTHONPATH to include it.")
    sys.exit(1)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_subsection(title: str) -> None:
    """Print a subsection header."""
    print(f"\n{title}")
    print("-" * len(title))


def print_dict(data: Dict[str, Any], indent: int = 0) -> None:
    """Print a dictionary with indentation."""
    for key, value in data.items():
        prefix = "  " * indent
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 1)
        elif isinstance(value, bool):
            print(f"{prefix}{key}: {'yes' if value else 'no'}")
        else:
            print(f"{prefix}{key}: {value}")


def safe_check_resources(config, args) -> Tuple[bool, List[str]]:
    """Safely check system resources. Non-critical; always continues."""
    warnings: List[str] = []
    try:
        print_subsection("System Resources")
        resources = config.diagnostics.detect_system_resources()
        if resources and resources.total_ram_gb > 0:
            print(f"Total RAM: {resources.total_ram_gb:.2f} GB")
            print(f"Available RAM: {resources.available_ram_gb:.2f} GB")
            print(f"CPU Cores: {resources.cpu_cores}")
            if resources.cpu_freq_mhz > 0:
                print(f"CPU Frequency: {resources.cpu_freq_mhz:.2f} MHz")
            print(f"GPU Available: {'yes' if resources.gpu_available else 'no'}")
            if resources.gpu_info:
                print(f"GPU Info: {resources.gpu_info}")
        else:
            print("[WARN] System resource detection unavailable; skipping resource checks.")

        compatibility = config.diagnostics.check_profile_compatibility(config.profile_config)
        print_subsection("Profile Compatibility")
        if compatibility["compatible"]:
            print("[OK] Profile is compatible with detected resources.")
        else:
            print("[WARN] Profile may exceed detected local resources.")

        for warning in compatibility["warnings"]:
            print(f"  [WARN] {warning}")
            warnings.append(warning)

        for error in compatibility["errors"]:
            print(f"  [ERROR] {error}")
            warnings.append(error)

        return True, warnings
    except Exception as exc:
        logger.warning("System resource check failed: %s", exc)
        print(f"[WARN] System resource check unavailable: {exc}")
        return True, [f"System resource check failed: {exc}"]


def safe_check_models(config, args) -> Tuple[bool, List[str]]:
    """Safely check model capabilities. Non-critical; continues gracefully."""
    try:
        print_subsection("Model Capabilities")
        model_capabilities = config.model_manager.check_capabilities()
        for model_type, capability in model_capabilities.items():
            status = "[OK]" if capability.get("available") else "[WARN]"
            reason = capability.get("reason", "unknown")
            print(f"{status} {model_type}: {reason}")

            if args.verbose and "available_models" in capability:
                print(f"  Available models: {capability['available_models']}")

        return True, []
    except Exception as exc:
        logger.warning("Model capability check failed: %s", exc)
        print(f"[WARN] Model capability check failed: {exc}")
        return True, [f"Model capability check failed: {exc}"]


def safe_check_features(config, args) -> Tuple[bool, List[str]]:
    """Safely check feature dependencies and apply fallbacks."""
    try:
        print_subsection("Feature Dependencies")
        feature_dependencies = config.feature_manager.check_dependencies()
        for feature_name, dep_status in feature_dependencies.items():
            status = "[OK]" if dep_status.get("available") else "[WARN]"
            reason = dep_status.get("reason", "unknown")
            print(f"{status} {feature_name}: {reason}")

            if args.verbose and "missing" in dep_status:
                print(f"  Missing dependencies: {dep_status['missing']}")

        print_subsection("Feature Fallbacks")
        try:
            model_capabilities = config.model_manager.check_capabilities()
            config.feature_manager.apply_fallbacks(model_capabilities)
        except Exception as exc:
            logger.warning("Feature fallback application failed: %s", exc)

        enabled_features = config.feature_manager.get_enabled_features()
        print(f"Enabled features: {', '.join(enabled_features) if enabled_features else 'None'}")

        if args.verbose:
            print("\nFeature states:")
            for feature_name, feature in config.feature_manager.features.items():
                state = feature.state.value
                reason = f" ({feature.error_message})" if feature.error_message else ""
                print(f"  {feature_name}: {state}{reason}")

        return True, []
    except Exception as exc:
        logger.warning("Feature dependency check failed: %s", exc)
        print(f"[WARN] Feature dependency check failed: {exc}")
        return True, [f"Feature dependency check failed: {exc}"]


def safe_check_services(config, args) -> Tuple[bool, List[str]]:
    """Safely check service health. Non-critical; only runs in verbose mode."""
    if not args.verbose:
        return True, []

    try:
        print_subsection("Service Health Checks")
        services = {
            "qdrant": f"{config.qdrant_url}/",
            "ollama": f"{config.ollama_base_url}/api/tags",
            "reranker": f"{config.reranker_url}/health",
        }
        service_health = config.check_service_health(services)
        if not service_health:
            print("[WARN] Service health checks unavailable.")
            return True, ["Service health checks unavailable"]

        for service_name, health in service_health.items():
            status = "[OK]" if health.healthy else "[WARN]"
            print(f"{status} {service_name}: {health.url}")
            if health.error_message:
                print(f"  Info: {health.error_message}")

        return True, []
    except Exception as exc:
        logger.warning("Service health check failed: %s", exc)
        print(f"[WARN] Service health check failed: {exc}")
        return True, [f"Service health check failed: {exc}"]


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Validate startup configuration for compliance-agent-rag"
    )
    parser.add_argument(
        "--profile",
        type=str,
        choices=["local-lite", "local-full", "cloud-lite", "cloud-production"],
        default=None,
        help="Deployment profile to validate. Defaults to DEPLOYMENT_PROFILE or local-lite.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    return parser


def main() -> int:
    """Run startup validation."""
    args = build_parser().parse_args()
    if args.json or not args.verbose:
        logging.getLogger().setLevel(logging.CRITICAL)

    try:
        config = get_config(args.profile)
    except Exception as exc:
        payload = {"status": "error", "error": str(exc), "profile": args.profile}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"[ERROR] Failed to load configuration: {exc}")
        return 1

    validation_results = config.validate()

    if args.json:
        diagnostics = None
        diagnostic_warning = None
        if validation_results.get("valid"):
            try:
                diagnostics = config.run_diagnostics()
            except Exception as exc:
                diagnostic_warning = f"Diagnostics failed: {exc}"

        results = {
            "profile": config.profile_name,
            "status": "success" if validation_results.get("valid") else "error",
            "validation": validation_results,
            "diagnostics": diagnostics,
            "diagnostic_warning": diagnostic_warning,
            "summary": config.get_summary(),
        }
        print(json.dumps(results, indent=2))
        return 0 if validation_results.get("valid") else 1

    print_section("COMPLIANCE AGENT RAG - STARTUP VALIDATION")

    print_subsection("Deployment Profile")
    print(f"Profile: {config.profile_name}")
    if config.profile_config:
        print(f"Description: {config.profile_config.description}")
        print("\nResource Requirements:")
        print(f"  Min RAM: {config.profile_config.min_ram_gb} GB")
        print(f"  Recommended RAM: {config.profile_config.recommended_ram_gb} GB")
        print(f"  CPU Cores: {config.profile_config.cpu_cores}")
        print(f"  GPU Required: {'yes' if config.profile_config.gpu_required else 'no'}")
        print(f"  GPU Optional: {'yes' if config.profile_config.gpu_optional else 'no'}")

    print_subsection("Configuration Validation")
    if validation_results["valid"]:
        print("[OK] Configuration is valid.")
    else:
        print("[ERROR] Configuration has errors.")

    if validation_results["errors"]:
        print("\nErrors:")
        for error in validation_results["errors"]:
            print(f"  [ERROR] {error}")

    if validation_results["warnings"]:
        print("\nWarnings:")
        for warning in validation_results["warnings"]:
            print(f"  [WARN] {warning}")

    safe_check_resources(config, args)
    safe_check_models(config, args)
    safe_check_features(config, args)
    safe_check_services(config, args)

    if args.verbose:
        print_subsection("Configuration Summary")
        print_dict(config.get_summary())

    print_section("VALIDATION COMPLETE")
    if not validation_results["valid"]:
        print("[ERROR] Validation failed. Address the errors above before startup.")
        return 1

    print("[OK] Validation successful. System is ready to start.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[WARN] Validation interrupted by user")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}")
        logging.exception("Unexpected startup validation failure")
        sys.exit(1)
