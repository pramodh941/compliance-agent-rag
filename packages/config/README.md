# Centralized Configuration System

This package provides unified configuration management for compliance-agent-rag with deployment profiles, model configuration, feature toggles, and startup diagnostics.

## Overview

The configuration system is designed to:
- Centralize all configuration in one place
- Support multiple deployment profiles (local-lite, local-full, cloud-lite, cloud-production)
- Provide graceful fallbacks for optional features
- Enable runtime capability checks
- Validate configuration at startup
- Maintain backward compatibility with existing code

## Architecture

```
packages/config/
├── __init__.py          # Main entry point
├── core.py              # Core Config class
├── profiles.py          # Deployment profile definitions
├── models.py            # Model configuration and capability detection
├── features.py          # Feature toggles and fallbacks
├── diagnostics.py       # Startup diagnostics and health checks
└── validation.py        # Configuration validation utilities
```

## Usage

### Basic Usage

```python
from packages.config import get_config

# Get configuration (uses DEPLOYMENT_PROFILE env var)
config = get_config()

# Validate configuration
validation_results = config.validate()

# Run diagnostics
diagnostics = config.run_diagnostics()

# Get configuration summary
summary = config.get_summary()
```

### Using Specific Profile

```python
from packages.config import get_config

# Load specific profile
config = get_config(profile_name="local-full")

# Profile information
print(f"Profile: {config.profile_name}")
print(f"Description: {config.profile_config.description}")
```

### Accessing Configuration

```python
from packages.config import get_config

config = get_config()

# Database configuration
print(f"PostgreSQL URL: {config.postgres_url}")
print(f"Qdrant URL: {config.qdrant_url}")

# Model configuration
if config.model_manager.llm_model:
    print(f"LLM Model: {config.model_manager.llm_model.name}")
if config.model_manager.embedding_model:
    print(f"Embedding Model: {config.model_manager.embedding_model.name}")

# Feature toggles
print(f"Reranker enabled: {config.feature_manager.is_enabled('reranker')}")
print(f"OCR enabled: {config.feature_manager.is_enabled('ocr')}")

# Ingestion settings
print(f"Chunk size: {config.chunk_size}")
print(f"Chunk overlap: {config.chunk_overlap}")
```

### Checking Capabilities

```python
from packages.config import get_config

config = get_config()

# Check model capabilities
capabilities = config.model_manager.check_capabilities()
print(f"LLM available: {capabilities['llm']['available']}")
print(f"Embedding available: {capabilities['embedding']['available']}")
print(f"Reranker available: {capabilities['reranker']['available']}")

# Check feature dependencies
dependencies = config.feature_manager.check_dependencies()
for feature, status in dependencies.items():
    print(f"{feature}: {status['available']}")

# Apply fallbacks based on capabilities
config.feature_manager.apply_fallbacks(capabilities)
```

### Service Health Checks

```python
from packages.config import get_config

config = get_config()

# Check service health
services = {
    "qdrant": config.qdrant_url,
    "ollama": f"{config.ollama_base_url}/api/tags",
    "reranker": f"{config.reranker_url}/health",
}

health_status = config.check_service_health(services)
for service_name, health in health_status.items():
    print(f"{service_name}: {'healthy' if health.healthy else 'unhealthy'}")
```

### Generating Environment Files

```python
from packages.config import get_config

config = get_config()

# Get configuration as environment variable dictionary.
# Secrets are masked by default for safe diagnostics/debugging.
env_dict = config.get_env_dict()

# Use include_secrets=True only for trusted runtime handoff paths
# that must receive raw credentials.
runtime_env = config.get_env_dict(include_secrets=True)

# Write safe debug output
with open('.env.debug', 'w') as f:
    for key, value in env_dict.items():
        f.write(f"{key}={value}\n")
```

## Deployment Profiles

### local-lite

Minimal resources, CPU-only, ~4GB RAM.

- **Models**: gemma:2b, nomic-embed-text
- **Features**: Basic ingestion only (no OCR, no reranker)
- **Performance**: Lower batch sizes, fewer concurrent docs

### local-full

Full local development with optional GPU support.

- **Models**: llama3:8b, nomic-embed-text, cross-encoder/ms-marco-MiniLM-L-6-v2
- **Features**: All features enabled (OCR, reranker, advanced parsing)
- **Performance**: Higher batch sizes, more concurrent docs

### cloud-lite

Minimal cloud deployment for cost optimization.

- **Models**: gemma:2b, nomic-embed-text (can use cloud APIs)
- **Features**: Basic ingestion only
- **Performance**: Cloud-optimized timeouts and batch sizes

### cloud-production

Full production deployment with all features.

- **Models**: llama3:8b, nomic-embed-text, cross-encoder/ms-marco-MiniLM-L-6-v2 (can use cloud APIs)
- **Features**: All features enabled
- **Performance**: Production-optimized settings

See [DEPLOYMENT_PROFILES.md](../../DEPLOYMENT_PROFILES.md) for detailed information.

## Feature Toggles

Features can be enabled/disabled via environment variables:

```bash
ENABLE_RERANKING=true
ENABLE_OCR=true
ENABLE_LAYOUT_PARSING=true
ENABLE_TABLE_EXTRACTION=true
ENABLE_IMAGE_EXTRACTION=true
ENABLE_SEMANTIC_CHUNKING=true
ENABLE_HIERARCHY_DETECTION=true
ENABLE_METADATA_EXTRACTION=true
```

Features have graceful fallback behavior when dependencies are unavailable. For example:
- If reranker is unavailable, the system falls back to dense retrieval only
- If OCR is unavailable, scanned pages are skipped
- If semantic chunking is unavailable, simple chunking is used

## Model Configuration

Models are configured in the `ModelConfig` class with capability information:

```python
from packages.config.models import ModelConfig, ModelProvider

model = ModelConfig(
    name="gemma:2b",
    provider=ModelProvider.OLLAMA,
    enabled=True,
    supports_generation=True,
    min_ram_gb=2.0,
    requires_gpu=False,
)
```

The model manager automatically checks if models are available and provides fallback options.

## Validation

The configuration system includes comprehensive validation:

```python
from packages.config import get_config

config = get_config()

# Validate configuration
validation = config.validate()
if not validation["valid"]:
    print("Configuration errors:", validation["errors"])
    print("Configuration warnings:", validation["warnings"])
```

Validation checks:
- Database configuration
- Service URLs
- Model names
- Timeout ranges
- Port numbers
- Chunking parameters
- Feature dependencies

## Diagnostics

The diagnostics module provides system resource detection and health checks:

```python
from packages.config import get_config

config = get_config()

# Detect system resources
resources = config.diagnostics.detect_system_resources()
print(f"Total RAM: {resources.total_ram_gb} GB")
print(f"CPU Cores: {resources.cpu_cores}")
print(f"GPU Available: {resources.gpu_available}")

# Check profile compatibility
compatibility = config.diagnostics.check_profile_compatibility(config.profile_config)
if not compatibility["compatible"]:
    print("System not compatible with profile:", compatibility["errors"])
```

## Backward Compatibility

The configuration system maintains backward compatibility with existing code:

```python
# Old way (still works)
from app.core.config import settings
print(settings.EMBEDDING_MODEL)

# New way (recommended)
from packages.config import get_config
config = get_config()
print(config.model_manager.embedding_model.name)
```

Existing configuration classes (`Settings`, `IngestionConfig`) now wrap the centralized configuration system, so existing code continues to work without modification.

## Environment Variables

### Core Configuration

- `DEPLOYMENT_PROFILE`: Deployment profile to use (local-lite, local-full, cloud-lite, cloud-production)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Database Configuration

- `POSTGRES_HOST`: PostgreSQL host
- `POSTGRES_PORT`: PostgreSQL port
- `POSTGRES_USER`: PostgreSQL username
- `POSTGRES_PASSWORD`: PostgreSQL password
- `POSTGRES_DB`: PostgreSQL database name
- `QDRANT_URL`: Qdrant vector database URL

### Service URLs

- `OLLAMA_BASE_URL`: Ollama service URL
- `MCP_BASE_URL`: MCP server URL
- `AGENT_WORKER_URL`: Agent worker URL
- `RERANKER_URL`: Reranker service URL

### Model Configuration

- `LLM_MODEL`: LLM model name
- `EMBEDDING_MODEL`: Embedding model name
- `RERANKER_MODEL`: Reranker model name

### Feature Toggles

- `ENABLE_RERANKING`: Enable/disable reranker
- `ENABLE_OCR`: Enable/disable OCR
- `ENABLE_LAYOUT_PARSING`: Enable/disable layout parsing
- `ENABLE_TABLE_EXTRACTION`: Enable/disable table extraction
- `ENABLE_IMAGE_EXTRACTION`: Enable/disable image extraction
- `ENABLE_SEMANTIC_CHUNKING`: Enable/disable semantic chunking
- `ENABLE_HIERARCHY_DETECTION`: Enable/disable hierarchy detection
- `ENABLE_METADATA_EXTRACTION`: Enable/disable metadata extraction

### Ingestion Configuration

- `CHUNK_SIZE`: Chunk size for document splitting
- `CHUNK_OVERLAP`: Chunk overlap
- `MIN_CHUNK_SIZE`: Minimum chunk size
- `PDF_PARSER`: PDF parser to use (pypdf, pdfplumber, pymupdf)
- `CHUNKING_STRATEGY`: Chunking strategy (simple, semantic, hierarchical, recursive)

### Performance Configuration

- `API_REQUEST_TIMEOUT`: API request timeout in seconds
- `AGENT_RUN_TIMEOUT`: Agent run timeout in seconds
- `PLANNER_TIMEOUT`: Planner timeout in seconds
- `MCP_TIMEOUT`: MCP timeout in seconds
- `DENSE_RETRIEVAL_LIMIT`: Dense retrieval limit
- `SPARSE_RETRIEVAL_K`: Sparse retrieval K
- `RERANK_TOP_K`: Rerank top K
- `EMBEDDING_BATCH_SIZE`: Embedding batch size
- `MAX_CONCURRENT_DOCS`: Maximum concurrent documents

## Testing

```python
# Test configuration loading
from packages.config import get_config

config = get_config("local-lite")
assert config.profile_name == "local-lite"

# Test validation
validation = config.validate()
assert validation["valid"] == True

# Test capability checks
capabilities = config.model_manager.check_capabilities()
assert capabilities["embedding"]["available"] == True

# Test feature toggles
assert config.feature_manager.is_enabled("reranker") == False
```

## Troubleshooting

### Configuration Not Loading

If configuration fails to load:
1. Check that `DEPLOYMENT_PROFILE` environment variable is set
2. Verify profile name is valid (local-lite, local-full, cloud-lite, cloud-production)
3. Check that required environment variables are set
4. Run validation script: `python scripts/validate_startup.py`

### Models Not Available

If models are not available:
1. Check Ollama service is running
2. Verify model is pulled: `ollama list`
3. Pull model if needed: `ollama pull <model-name>`
4. Check model name in configuration
5. Run capability checks

### Feature Disabled Unexpectedly

If a feature is disabled:
1. Check feature toggle in environment variables
2. Verify dependencies are installed
3. Check capability diagnostics
4. Look for fallback messages in logs

## Contributing

When adding new configuration options:

1. Add to appropriate section in `core.py` (Config class)
2. Add validation in `validation.py` if needed
3. Add to profile definitions in `profiles.py`
4. Update environment file examples
5. Update documentation

## License

This configuration system is part of the compliance-agent-rag project.
