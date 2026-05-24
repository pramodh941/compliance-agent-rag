#!/usr/bin/env python3
"""
Phase 5 configuration smoke tests.

Focus areas:
1. Optional dependencies warn and continue.
2. All supported profiles load with appropriate credentials.
3. Cloud production rejects missing or placeholder credentials.
4. Invalid profiles fail cleanly.
5. Summaries and debug env dictionaries do not expose secrets.
"""

import logging
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from packages.config import Config, get_config, reset_config


@contextmanager
def temporary_env(updates: Dict[str, Optional[str]]) -> Iterator[None]:
    """Temporarily update environment variables for a smoke test."""
    original = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        reset_config()


def test_profile(profile_name: str) -> bool:
    """Smoke test a single profile."""
    print(f"\n{'=' * 60}")
    print(f"Testing profile: {profile_name}")
    print(f"{'=' * 60}")

    env_updates = {"DEPLOYMENT_PROFILE": profile_name}
    if profile_name.startswith("cloud-"):
        env_updates.update(
            {
                "POSTGRES_USER": "phase5_user",
                "POSTGRES_PASSWORD": "phase5_strong_password",
            }
        )

    with temporary_env(env_updates):
        try:
            reset_config()
            config = get_config(profile_name)
            validation = config.validate()

            if not validation["valid"]:
                print(f"[FAIL] Validation failed for {profile_name}")
                for error in validation["errors"]:
                    print(f"  - {error}")
                return False

            print("[OK] Configuration is valid")
            for warning in validation["warnings"]:
                print(f"  [WARN] {warning}")

            resources = config.diagnostics.detect_system_resources()
            if resources:
                print("[OK] System resources detected or gracefully unavailable")

            compatibility = config.diagnostics.check_profile_compatibility(config.profile_config)
            if compatibility["compatible"]:
                print("[OK] Profile compatibility check completed")
            else:
                print("[WARN] Compatibility check produced resource warnings")

            config.model_manager.check_capabilities()
            print("[OK] Model capability check completed")

            config.feature_manager.check_dependencies()
            print("[OK] Feature dependency check completed")

            print(f"[OK] Profile '{profile_name}' passed")
            return True
        except Exception as exc:
            print(f"[FAIL] Profile '{profile_name}' raised unexpectedly: {exc}")
            import traceback

            traceback.print_exc()
            return False


def test_cloud_production_requires_credentials() -> bool:
    """Cloud production must not silently accept missing credentials."""
    print("\nTesting cloud-production credential enforcement")
    with temporary_env(
        {
            "DEPLOYMENT_PROFILE": "cloud-production",
            "POSTGRES_USER": "phase5_user",
            "POSTGRES_PASSWORD": None,
        }
    ):
        config = Config(profile_name="cloud-production")
        validation = config.validate()
        if validation["valid"]:
            print("[FAIL] cloud-production accepted missing POSTGRES_PASSWORD")
            return False
        print("[OK] cloud-production rejects missing POSTGRES_PASSWORD")
        return True


def test_cloud_production_rejects_placeholders() -> bool:
    """Cloud production must reject unexpanded secret placeholders."""
    print("\nTesting cloud-production placeholder rejection")
    with temporary_env(
        {
            "DEPLOYMENT_PROFILE": "cloud-production",
            "POSTGRES_USER": "${CLOUD_SQL_USER}",
            "POSTGRES_PASSWORD": "${CLOUD_SQL_PASSWORD}",
        }
    ):
        config = Config(profile_name="cloud-production")
        validation = config.validate()
        if validation["valid"]:
            print("[FAIL] cloud-production accepted placeholder credentials")
            return False
        print("[OK] cloud-production rejects placeholder credentials")
        return True


def test_invalid_profile_fails_cleanly() -> bool:
    """Invalid profiles should fail with a useful ValueError."""
    print("\nTesting invalid profile handling")
    with temporary_env({"DEPLOYMENT_PROFILE": "not-a-profile"}):
        try:
            Config()
        except ValueError as exc:
            if "Invalid deployment profile" in str(exc):
                print("[OK] Invalid profile produced a clear error")
                return True
            print(f"[FAIL] Invalid profile error was not actionable: {exc}")
            return False
    print("[FAIL] Invalid profile did not fail")
    return False


def test_secret_masking() -> bool:
    """Summaries and safe env output must not leak raw credentials."""
    print("\nTesting secret masking")
    secret = "phase5_super_secret"
    with temporary_env(
        {
            "DEPLOYMENT_PROFILE": "cloud-production",
            "POSTGRES_USER": "phase5_user",
            "POSTGRES_PASSWORD": secret,
        }
    ):
        config = Config(profile_name="cloud-production")
        summary = repr(config.get_summary())
        safe_env = repr(config.get_safe_env_dict())
        default_env = repr(config.get_env_dict())
        raw_env = config.get_env_dict(include_secrets=True)

        if secret in summary or secret in safe_env or secret in default_env:
            print("[FAIL] Raw secret leaked through summary or safe env output")
            return False
        if raw_env["POSTGRES_PASSWORD"] != secret:
            print("[FAIL] include_secrets=True did not preserve runtime password")
            return False

        print("[OK] Secrets are masked by default and available only when requested")
        return True


def main() -> int:
    """Run all Phase 5 smoke tests."""
    profiles = ["local-lite", "local-full", "cloud-lite", "cloud-production"]

    print("\n" + "=" * 60)
    print("PHASE 5 CONFIGURATION SMOKE TESTS")
    print("=" * 60)

    results = {profile: test_profile(profile) for profile in profiles}
    results["cloud-production-credentials"] = test_cloud_production_requires_credentials()
    results["cloud-production-placeholders"] = test_cloud_production_rejects_placeholders()
    results["invalid-profile"] = test_invalid_profile_fails_cleanly()
    results["secret-masking"] = test_secret_masking()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for value in results.values() if value)
    total = len(results)

    for name, passed_test in results.items():
        print(f"{'[OK]' if passed_test else '[FAIL]'} {name}")

    print(f"\nTotal: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
