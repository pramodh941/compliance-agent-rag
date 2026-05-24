"""
Configuration validation utilities.

Provides validation functions for:
- Environment variables
- Model configurations
- Feature dependencies
- Deployment profile compatibility
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Configuration validation error."""
    pass


class ValidationWarning(Exception):
    """Configuration validation warning (non-fatal)."""
    pass


def validate_env_var(
    name: str,
    required: bool = True,
    pattern: Optional[str] = None,
    min_length: int = 0,
    max_length: int = 1000,
) -> Tuple[bool, Optional[str]]:
    """
    Validate an environment variable.
    
    Args:
        name: Environment variable name
        required: Whether the variable is required
        pattern: Regex pattern to match (optional)
        min_length: Minimum string length
        max_length: Maximum string length
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    value = os.getenv(name)
    
    # Check if required
    if required and not value:
        return False, f"Required environment variable {name} is not set"
    
    # Check length
    if value:
        if len(value) < min_length:
            return False, f"{name} is too short (min {min_length} characters)"
        if len(value) > max_length:
            return False, f"{name} is too long (max {max_length} characters)"
    
    # Check pattern
    if value and pattern:
        if not re.match(pattern, value):
            return False, f"{name} does not match required pattern: {pattern}"
    
    return True, None


def validate_url(url: str, allow_localhost: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate a URL string.
    
    Args:
        url: URL to validate
        allow_localhost: Whether localhost URLs are allowed
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL is empty"
    
    # Basic URL pattern
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    if not re.match(pattern, url):
        return False, f"Invalid URL format: {url}"
    
    # Check localhost
    if not allow_localhost and 'localhost' in url.lower():
        return False, "localhost URLs are not allowed in production"
    
    return True, None


def validate_port(port: int, min_port: int = 1, max_port: int = 65535) -> Tuple[bool, Optional[str]]:
    """
    Validate a port number.
    
    Args:
        port: Port number to validate
        min_port: Minimum valid port
        max_port: Maximum valid port
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int):
        return False, f"Port must be an integer, got {type(port)}"
    
    if port < min_port or port > max_port:
        return False, f"Port {port} outside valid range ({min_port}-{max_port})"
    
    return True, None


def validate_timeout(timeout: int, min_seconds: int = 1, max_seconds: int = 3600) -> Tuple[bool, Optional[str]]:
    """
    Validate a timeout value.
    
    Args:
        timeout: Timeout in seconds
        min_seconds: Minimum valid timeout
        max_seconds: Maximum valid timeout
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(timeout, int):
        return False, f"Timeout must be an integer, got {type(timeout)}"
    
    if timeout < min_seconds or timeout > max_seconds:
        return False, f"Timeout {timeout}s outside valid range ({min_seconds}-{max_seconds}s)"
    
    return True, None


def validate_model_name(model_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a model name.
    
    Args:
        model_name: Model name to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not model_name:
        return False, "Model name is empty"
    
    # Basic validation - allow alphanumeric, hyphens, colons, slashes
    pattern = r'^[a-zA-Z0-9_:/\-\.]+$'
    if not re.match(pattern, model_name):
        return False, f"Invalid model name format: {model_name}"
    
    return True, None


def validate_positive_int(value: int, name: str = "value") -> Tuple[bool, Optional[str]]:
    """
    Validate a positive integer.
    
    Args:
        value: Value to validate
        name: Name of the value for error messages
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, int):
        return False, f"{name} must be an integer, got {type(value)}"
    
    if value <= 0:
        return False, f"{name} must be positive, got {value}"
    
    return True, None


def validate_range(
    value: int,
    name: str,
    min_val: int,
    max_val: int,
) -> Tuple[bool, Optional[str]]:
    """
    Validate a value is within a range.
    
    Args:
        value: Value to validate
        name: Name of the value for error messages
        min_val: Minimum valid value
        max_val: Maximum valid value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(value, int):
        return False, f"{name} must be an integer, got {type(value)}"
    
    if value < min_val or value > max_val:
        return False, f"{name} ({value}) outside valid range ({min_val}-{max_val})"
    
    return True, None


def validate_config_dict(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Validate a configuration dictionary against a schema.
    
    Args:
        config: Configuration dictionary to validate
        schema: Schema dictionary with validation rules
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    for key, rules in schema.items():
        if key not in config:
            if rules.get("required", False):
                errors.append(f"Missing required field: {key}")
            continue
        
        value = config[key]
        
        # Type validation
        if "type" in rules:
            expected_type = rules["type"]
            if not isinstance(value, expected_type):
                errors.append(f"{key} must be {expected_type.__name__}, got {type(value).__name__}")
                continue
        
        # Range validation
        if "min" in rules and value < rules["min"]:
            errors.append(f"{key} ({value}) below minimum ({rules['min']})")
        
        if "max" in rules and value > rules["max"]:
            errors.append(f"{key} ({value}) above maximum ({rules['max']})")
        
        # Choice validation
        if "choices" in rules and value not in rules["choices"]:
            errors.append(f"{key} ({value}) not in valid choices: {rules['choices']}")
    
    return errors


def validate_postgres_config(
    host: str,
    port: int,
    user: str,
    password: str,
    database: str,
) -> List[str]:
    """
    Validate PostgreSQL configuration.
    
    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        user: PostgreSQL user
        password: PostgreSQL password
        database: Database name
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not host:
        errors.append("POSTGRES_HOST is required")
    
    is_valid, error = validate_port(port)
    if not is_valid:
        errors.append(f"POSTGRES_PORT: {error}")
    
    if not user:
        errors.append("POSTGRES_USER is required")
    
    if not password:
        errors.append("POSTGRES_PASSWORD is required")
    
    if not database:
        errors.append("POSTGRES_DB is required")
    
    # Warn about default credentials
    if user == "admin" and password == "admin":
        logger.warning("Using default PostgreSQL credentials (admin/admin). "
                      "Set POSTGRES_USER and POSTGRES_PASSWORD for production.")
    
    return errors


def validate_qdrant_config(url: str) -> List[str]:
    """
    Validate Qdrant configuration.
    
    Args:
        url: Qdrant URL
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not url:
        errors.append("QDRANT_URL is required")
        return errors
    
    is_valid, error = validate_url(url, allow_localhost=True)
    if not is_valid:
        errors.append(f"QDRANT_URL: {error}")
    
    return errors


def validate_ingestion_config(
    chunk_size: int,
    chunk_overlap: int,
    pdf_parser: str,
    chunking_strategy: str,
) -> List[str]:
    """
    Validate ingestion configuration.
    
    Args:
        chunk_size: Chunk size
        chunk_overlap: Chunk overlap
        pdf_parser: PDF parser to use
        chunking_strategy: Chunking strategy
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    is_valid, error = validate_range(chunk_size, "CHUNK_SIZE", 100, 2000)
    if not is_valid:
        errors.append(error)
    
    is_valid, error = validate_range(chunk_overlap, "CHUNK_OVERLAP", 0, chunk_size)
    if not is_valid:
        errors.append(error)
    
    valid_parsers = ["pypdf", "pdfplumber", "pymupdf"]
    if pdf_parser not in valid_parsers:
        errors.append(f"PDF_PARSER ({pdf_parser}) must be one of: {valid_parsers}")
    
    valid_strategies = ["simple", "semantic", "hierarchical", "recursive"]
    if chunking_strategy not in valid_strategies:
        errors.append(f"CHUNKING_STRATEGY ({chunking_strategy}) must be one of: {valid_strategies}")
    
    return errors


def run_all_validations(config_dict: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
    """
    Run all configuration validations.
    
    Args:
        config_dict: Configuration dictionary
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    # PostgreSQL
    postgres_errors = validate_postgres_config(
        host=config_dict.get("POSTGRES_HOST", ""),
        port=config_dict.get("POSTGRES_PORT", 5432),
        user=config_dict.get("POSTGRES_USER", ""),
        password=config_dict.get("POSTGRES_PASSWORD", ""),
        database=config_dict.get("POSTGRES_DB", ""),
    )
    errors.extend(postgres_errors)
    
    # Qdrant
    qdrant_errors = validate_qdrant_config(
        url=config_dict.get("QDRANT_URL", ""),
    )
    errors.extend(qdrant_errors)
    
    # Ingestion
    ingestion_errors = validate_ingestion_config(
        chunk_size=config_dict.get("CHUNK_SIZE", 800),
        chunk_overlap=config_dict.get("CHUNK_OVERLAP", 100),
        pdf_parser=config_dict.get("PDF_PARSER", "pypdf"),
        chunking_strategy=config_dict.get("CHUNKING_STRATEGY", "simple"),
    )
    errors.extend(ingestion_errors)
    
    # Models
    for model_key in ["LLM_MODEL", "EMBEDDING_MODEL", "RERANKER_MODEL"]:
        model_name = config_dict.get(model_key)
        if model_name:
            is_valid, error = validate_model_name(model_name)
            if not is_valid:
                errors.append(f"{model_key}: {error}")
    
    # Timeouts
    for timeout_key in ["API_REQUEST_TIMEOUT", "AGENT_RUN_TIMEOUT", "PLANNER_TIMEOUT"]:
        timeout = config_dict.get(timeout_key)
        if timeout:
            is_valid, error = validate_timeout(timeout, 1, 600)
            if not is_valid:
                errors.append(f"{timeout_key}: {error}")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings
