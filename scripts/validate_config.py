#!/usr/bin/env python3
"""
Configuration validation script for compliance-agent-rag platform.

Validates that all required environment variables are set and have valid values.
"""
import os
import sys

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # If dotenv is not available, just use existing environment
    pass

def validate_config():
    """Validate configuration and report issues."""
    errors = []
    warnings = []
    
    # Required variables
    required_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ]
    
    # Optional but recommended variables
    recommended_vars = [
        "QDRANT_URL",
        "OLLAMA_BASE_URL",
        "MCP_BASE_URL",
        "AGENT_WORKER_URL",
    ]
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"Missing required variable: {var}")
    
    # Check for default credentials
    if os.getenv("POSTGRES_USER") == "admin" and os.getenv("POSTGRES_PASSWORD") == "admin":
        warnings.append("Using default Postgres credentials (admin/admin). Set secure credentials for production.")
    
    # Validate timeout ranges
    api_timeout = int(os.getenv("API_REQUEST_TIMEOUT", "180"))
    if api_timeout < 1 or api_timeout > 600:
        warnings.append(f"API_REQUEST_TIMEOUT ({api_timeout}s) outside recommended range (1-600s)")
    
    agent_timeout = int(os.getenv("AGENT_RUN_TIMEOUT", "300"))
    if agent_timeout < 1 or agent_timeout > 900:
        warnings.append(f"AGENT_RUN_TIMEOUT ({agent_timeout}s) outside recommended range (1-900s)")
    
    # Validate port numbers
    postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
    if postgres_port < 1 or postgres_port > 65535:
        errors.append(f"Invalid POSTGRES_PORT: {postgres_port}")
    
    # Print results
    print("=== Configuration Validation ===")
    print()
    
    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"  ❌ {error}")
        print()
    
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
        print()
    
    if not errors and not warnings:
        print("✅ Configuration is valid")
        return 0
    elif errors:
        print(f"❌ Validation failed with {len(errors)} error(s)")
        return 1
    else:
        print(f"⚠️  Validation passed with {len(warnings)} warning(s)")
        return 0

if __name__ == "__main__":
    sys.exit(validate_config())
