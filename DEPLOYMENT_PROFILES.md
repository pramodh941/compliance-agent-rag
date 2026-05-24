# Deployment Profiles

This document describes the deployment profiles available in compliance-agent-rag, their hardware requirements, recommended defaults, and usage instructions.

## Overview

The system supports four deployment profiles designed for different use cases:

- **local-lite**: Minimal resources, CPU-only, ~4GB RAM
- **local-full**: Full local development with optional GPU support
- **cloud-lite**: Minimal cloud deployment for cost optimization
- **cloud-production**: Full production deployment with all features

## Profile Details

### local-lite

**Purpose**: Minimal local deployment for CPU-only systems with limited resources.

**Hardware Requirements**:
- **Minimum RAM**: 4 GB
- **Recommended RAM**: 8 GB
- **CPU Cores**: 2+
- **GPU**: Not required, not supported

**Features**:
- Reranker: Disabled
- OCR: Disabled
- Advanced PDF parsing: Disabled
- Semantic chunking: Disabled
- Table extraction: Disabled
- Image extraction: Disabled
- Hierarchy detection: Enabled
- Metadata extraction: Enabled

**Models**:
- LLM: `gemma:2b` (Ollama)
- Embedding: `nomic-embed-text` (Ollama)
- Reranker: Not configured

**Performance Settings**:
- Embedding batch size: 5
- Max concurrent docs: 2
- Dense retrieval limit: 5
- Sparse retrieval K: 5
- Rerank top K: 2

**Timeouts**:
- API request timeout: 180s
- Agent run timeout: 300s
- Planner timeout: 180s

**Use Cases**:
- Development on resource-constrained machines
- Testing and validation
- Quick prototyping
- CI/CD pipelines with limited resources

**How to Use**:
```bash
# Using Docker Compose
DEPLOYMENT_PROFILE=local-lite docker-compose up

# Using environment file
cp .env.local-lite .env
docker-compose up
```

---

### local-full

**Purpose**: Full local development environment with optional GPU support.

**Hardware Requirements**:
- **Minimum RAM**: 8 GB
- **Recommended RAM**: 16 GB
- **CPU Cores**: 4+
- **GPU**: Optional (recommended for better performance)

**Features**:
- Reranker: Enabled
- OCR: Enabled
- Advanced PDF parsing: Enabled
- Semantic chunking: Enabled
- Table extraction: Enabled
- Image extraction: Enabled
- Hierarchy detection: Enabled
- Metadata extraction: Enabled

**Models**:
- LLM: `llama3:8b` (Ollama) / `gemma:2b` (Gemma)
- Embedding: `nomic-embed-text` (Ollama)
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` (Infinity)

**Performance Settings**:
- Embedding batch size: 10
- Max concurrent docs: 4
- Dense retrieval limit: 5
- Sparse retrieval K: 5
- Rerank top K: 2

**Timeouts**:
- API request timeout: 180s
- Agent run timeout: 300s
- Planner timeout: 180s

**Use Cases**:
- Full-featured local development
- Testing all system features
- Performance benchmarking
- Pre-production validation

**How to Use**:
```bash
# Using Docker Compose with profile
DEPLOYMENT_PROFILE=local-full docker-compose --profile local-full up

# Using environment file
cp .env.local-full .env
docker-compose --profile local-full up
```

**Note**: The reranker service is only started when using the `local-full` profile.

---

### cloud-lite

**Purpose**: Minimal cloud deployment for cost-optimized scenarios.

**Hardware Requirements**:
- **Minimum RAM**: 4 GB
- **Recommended RAM**: 8 GB
- **CPU Cores**: 2+
- **GPU**: Not required

**Features**:
- Reranker: Disabled
- OCR: Disabled
- Advanced PDF parsing: Disabled
- Semantic chunking: Disabled
- Table extraction: Disabled
- Image extraction: Disabled
- Hierarchy detection: Enabled
- Metadata extraction: Enabled

**Models**:
- LLM: `gemma:2b` (Ollama) - can be overridden with cloud API
- Embedding: `nomic-embed-text` (Ollama) - can be overridden with cloud API
- Reranker: Not configured

**Performance Settings**:
- Embedding batch size: 10
- Max concurrent docs: 4
- Dense retrieval limit: 5
- Sparse retrieval K: 5
- Rerank top K: 2

**Timeouts**:
- API request timeout: 180s
- Agent run timeout: 300s
- Planner timeout: 180s

**Use Cases**:
- Cost-optimized cloud deployments
- Small-scale production workloads
- Development/testing in cloud environment
- MVP deployments

**How to Use**:
```bash
# Using environment file
cp .env.cloud-lite .env
# Edit .env to set cloud service URLs and API keys
docker-compose up
```

**Cloud Configuration**:
Set the following environment variables for cloud services:
- `CLOUD_SQL_HOST`: Cloud SQL instance host
- `CLOUD_SQL_USER`: Cloud SQL username
- `CLOUD_SQL_PASSWORD`: Cloud SQL password
- `QDRANT_CLOUD_URL`: Qdrant Cloud URL
- `OLLAMA_CLOUD_URL`: Ollama Cloud URL (or use OpenAI API)

**Optional Cloud Models**:
To use cloud API models instead of local Ollama:
```bash
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=your_openai_api_key
```

---

### cloud-production

**Purpose**: Full production deployment with all features enabled.

**Hardware Requirements**:
- **Minimum RAM**: 16 GB
- **Recommended RAM**: 32 GB
- **CPU Cores**: 8+
- **GPU**: Optional (recommended for better performance)

**Features**:
- Reranker: Enabled
- OCR: Enabled
- Advanced PDF parsing: Enabled
- Semantic chunking: Enabled
- Table extraction: Enabled
- Image extraction: Enabled
- Hierarchy detection: Enabled
- Metadata extraction: Enabled

**Models**:
- LLM: `llama3:8b` (Ollama) - can be overridden with cloud API
- Embedding: `nomic-embed-text` (Ollama) - can be overridden with cloud API
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2` (Infinity)

**Performance Settings**:
- Embedding batch size: 20
- Max concurrent docs: 8
- Dense retrieval limit: 10
- Sparse retrieval K: 10
- Rerank top K: 5

**Timeouts**:
- API request timeout: 300s
- Agent run timeout: 600s
- Planner timeout: 300s

**Use Cases**:
- Production deployments
- High-throughput workloads
- Enterprise applications
- Multi-user environments

**How to Use**:
```bash
# Using Docker Compose with profile
DEPLOYMENT_PROFILE=cloud-production docker-compose --profile cloud-production up

# Using environment file
cp .env.cloud-production .env
# Edit .env to set cloud service URLs and API keys
docker-compose --profile cloud-production up
```

**Cloud Configuration**:
Set the following environment variables for cloud services:
- `CLOUD_SQL_HOST`: Cloud SQL instance host
- `CLOUD_SQL_USER`: Cloud SQL username
- `CLOUD_SQL_PASSWORD`: Cloud SQL password
- `QDRANT_CLOUD_URL`: Qdrant Cloud URL
- `OLLAMA_CLOUD_URL`: Ollama Cloud URL (or use OpenAI API)
- `RERANKER_CLOUD_URL`: Reranker service URL

**Optional Cloud Models**:
To use cloud API models instead of local Ollama:
```bash
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
RERANKER_MODEL=openai-reranker
OPENAI_API_KEY=your_openai_api_key
```

**Security Notes**:
- Never commit `.env.cloud-production` to version control
- Use secret management for sensitive credentials
- Set strong passwords for database
- Configure proper CORS and security headers
- Enable HTTPS in production

---

## Startup Validation

Before starting the application, run the startup validation script to check system compatibility:

```bash
# Validate default profile
python scripts/validate_startup.py

# Validate specific profile
python scripts/validate_startup.py --profile local-full

# Verbose output
python scripts/validate_startup.py --profile cloud-production --verbose

# JSON output for automation
python scripts/validate_startup.py --profile local-lite --json
```

The validation script checks:
- Configuration validity
- System resource availability
- Profile compatibility
- Model availability
- Feature dependencies
- Service health (optional)

---

## Docker Compose Profiles

Docker Compose profiles allow you to selectively start services:

```bash
# Start core services only (local-lite)
docker-compose up

# Start all services including reranker (local-full)
docker-compose --profile local-full up

# Start production services (cloud-production)
docker-compose --profile cloud-production up
```

**Service availability by profile**:

| Service | local-lite | local-full | cloud-lite | cloud-production |
|---------|-----------|------------|------------|------------------|
| API | ✓ | ✓ | ✓ | ✓ |
| Agent Worker | ✓ | ✓ | ✓ | ✓ |
| MCP Server | ✓ | ✓ | ✓ | ✓ |
| PostgreSQL | ✓ | ✓ | ✓ | ✓ |
| Qdrant | ✓ | ✓ | ✓ | ✓ |
| Ollama | ✓ | ✓ | ✓ | ✓ |
| Reranker | ✗ | ✓ | ✗ | ✓ |

---

## Feature Toggle Behavior

Features have graceful fallback behavior when dependencies are unavailable:

| Feature | Fallback Behavior |
|---------|------------------|
| Reranker | Use dense retrieval only |
| OCR | Skip scanned pages |
| Layout parsing | Use simple text extraction |
| Table extraction | Skip tables |
| Image extraction | Skip images |
| Semantic chunking | Use simple chunking |
| Hierarchy detection | Flat chunking |
| Metadata extraction | Minimal metadata |

---

## Cloud Run Recommendations

For Google Cloud Run deployments:

1. **Use cloud-production profile** for production workloads
2. **Set appropriate resource limits**:
   - CPU: 2-4 vCPUs
   - Memory: 4-8 GB (depending on profile)
   - Max instances: 10-100 (based on traffic)
3. **Use managed services**:
   - Cloud SQL for PostgreSQL
   - Qdrant Cloud for vector database
   - Cloud Storage for document storage
4. **Configure environment variables** via Cloud Run console or gcloud
5. **Enable VPC connector** for private service access
6. **Set up monitoring and logging** with Cloud Monitoring
7. **Use secret manager** for sensitive credentials

Example Cloud Run deployment:
```bash
gcloud run deploy compliance-api \
  --image gcr.io/PROJECT-ID/compliance-api \
  --platform managed \
  --region us-central1 \
  --cpu 4 \
  --memory 8Gi \
  --max-instances 100 \
  --env-vars-file .env.cloud-production
```

---

## Troubleshooting

### Out of Memory Errors

If you encounter OOM errors:
- Switch to a lighter profile (e.g., local-full → local-lite)
- Reduce batch sizes in environment variables
- Increase system RAM or use a machine with more resources
- Disable optional features (OCR, semantic chunking)

### Model Not Available

If a model is not available:
- Run `ollama pull <model-name>` to download the model
- Check Ollama service is running: `curl http://localhost:11434/api/tags`
- Verify model name in configuration
- Check model compatibility with your system

### Service Connection Errors

If services cannot connect:
- Verify all services are running: `docker-compose ps`
- Check network configuration
- Verify service URLs in environment variables
- Check firewall rules
- Use `docker-compose logs <service>` to debug

### Feature Disabled Unexpectedly

If a feature is disabled:
- Check feature toggle in environment variables
- Verify dependencies are installed
- Run validation script to check dependencies
- Check logs for fallback messages

---

## Migration Guide

### Migrating from Existing Configuration

If you have an existing deployment without profile-based configuration:

1. **Backup your current `.env` file**
2. **Choose an appropriate profile** based on your current setup
3. **Copy the corresponding environment file**:
   ```bash
   cp .env.local-lite .env  # or .env.local-full, etc.
   ```
4. **Update any custom values** from your backup
5. **Run validation**:
   ```bash
   python scripts/validate_startup.py
   ```
6. **Restart services**:
   ```bash
   docker-compose down
   docker-compose up
   ```

### Upgrading from local-lite to local-full

To upgrade your local deployment:

1. **Update environment file**:
   ```bash
   cp .env.local-full .env
   ```
2. **Pull additional models**:
   ```bash
   docker-compose exec ollama ollama pull llama3:8b
   ```
3. **Start with profile**:
   ```bash
   docker-compose --profile local-full up
   ```
4. **Run validation**:
   ```bash
   python scripts/validate_startup.py --profile local-full
   ```

---

## Best Practices

1. **Always run validation** before starting services
2. **Use appropriate profiles** for your environment
3. **Never commit production credentials** to version control
4. **Monitor resource usage** in production
5. **Test profile changes** in development first
6. **Keep dependencies updated** for security
7. **Use feature toggles** to control optional features
8. **Document custom configurations** for your team
9. **Regular backups** of database and vector store
10. **Graceful degradation** - system should work even if some features fail

---

## Additional Resources

- [Configuration API Reference](packages/config/README.md)
- [Docker Compose Documentation](docker-compose.yml)
- [Environment File Examples](.env.local-lite, .env.local-full, .env.cloud-lite, .env.cloud-production)
- [Startup Validation Script](scripts/validate_startup.py)
