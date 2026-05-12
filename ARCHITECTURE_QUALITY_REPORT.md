# Architecture Quality Report

**Date:** 2025-01-09
**Scope:** Architecture-quality, observability, and RAG-quality enhancement pass

---

## Dead Code and Empty Files

### Empty/Placeholder Files (Recommended for Removal)

The following files are empty or contain only placeholder content and appear to be unused:

**packages/rag/** (Empty/Placeholder Files):
- `packages/rag/pipeline.py` - Empty
- `packages/rag/retriever.py` - Empty
- `packages/rag/utils.py` - Empty
- `packages/rag/prompt_templates.py` - Empty

**packages/db/** (Empty/Placeholder Files):
- `packages/db/qdrant_client.py` - Empty
- `packages/db/postgres_client.py` - Empty

**packages/embeddings/** (Empty/Placeholder Files):
- `packages/embeddings/ollama.py` - Empty
- `packages/embeddings/base.py` - Contains only base class (no implementation)

**packages/reranker/** (Empty/Placeholder Files):
- `packages/reranker/cross_encoder.py` - Empty
- `packages/reranker/base.py` - Contains only base class (no implementation)

**apps/api/app/dependencies/**:
- `apps/api/app/dependencies/embeddings.py` - Empty

**Recommendation**: These files appear to be part of an intended modular architecture that was never fully implemented. The actual implementations are in:
- RAG: `apps/api/app/services/rag_service.py`
- Retrieval: `apps/api/app/services/hybrid_retriever.py`
- Embeddings: `apps/api/app/services/ollama_client.py`
- Reranker: `apps/api/app/dependencies/reranker.py`
- Qdrant: `apps/api/app/dependencies/qdrant.py`
- Postgres: `apps/api/app/dependencies/postgres.py`

**Action**: These empty files can be safely removed or kept as documentation of intended architecture. No impact on current functionality.

---

## Duplicated Logic

### Configuration Duplication
- `apps/api/app/core/config.py` - API configuration
- `apps/agent-worker/app/config.py` - Agent-worker configuration

**Issue**: Similar patterns for timeout validation, but different settings (appropriate for each service).

**Recommendation**: Keep separate - each service has different configuration needs.

### Logging Setup
- `apps/api/app/core/logging.py` - Custom JSON formatter
- `apps/agent-worker/app/main.py` - Simple logging.basicConfig()

**Issue**: Inconsistent logging approach between services.

**Recommendation**: For now, keep as-is. Agent-worker uses simple logging to avoid module dependency issues. Could standardize in future pass.

---

## Architecture Quality Issues

### 1. In-Memory Cache (Data Loss Risk)
**Location**: `apps/api/app/services/cache.py`
**Issue**: SimpleTTLCache is in-memory, data lost on restart
**Impact**: Lost cache hits after container restart, increased latency
**Recommendation**: Future enhancement - replace with Redis for persistence

### 2. BM25 Index Rebuilt on Startup
**Location**: `apps/api/app/services/hybrid_retriever.py`
**Issue**: BM25 index rebuilt from corpus on each startup
**Impact**: Slow startup if corpus is large
**Recommendation**: Future enhancement - persist BM25 index to disk or use Qdrant sparse search

### 3. Hardcoded Fallback Answer
**Location**: `apps/api/app/services/rag_service.py` (lines 236-243)
**Issue**: Hardcoded insider trading policy answer when LLM says "does not provide information"
**Impact**: Not generalizable, only works for specific queries
**Recommendation**: Remove fallback, let LLM handle all cases with improved prompt

### 4. One-Vector-Per-Policy Limitation
**Issue**: Documents chunked and stored, but no document-level metadata for retrieval
**Impact**: May miss policy-level context
**Recommendation**: Future enhancement - add document-level summaries and metadata

### 5. Simple Keyword Routing
**Location**: `apps/api/app/services/rag_service.py` (route_query function)
**Issue**: Simple keyword-based routing to collections
**Impact**: May route queries to wrong collection
**Recommendation**: Future enhancement - use embedding-based routing or classifier

---

## RAG Quality Issues

### 1. No Retrieval Quality Metrics
**Issue**: No metrics on retrieval precision/recall
**Impact**: Cannot measure or improve retrieval quality
**Status**: ✅ **FIXED** - Added comprehensive RAG metrics logging in Phase 3

### 2. No Evaluation Framework
**Issue**: No way to evaluate RAG performance systematically
**Impact**: Cannot detect regressions or improvements
**Status**: ✅ **FIXED** - Added lightweight evaluation script in Phase 3

### 3. Configurable Parameters Missing
**Issue**: Hard-coded retrieval limits and parameters
**Impact**: Cannot tune performance without code changes
**Status**: ✅ **FIXED** - Added configurable RAG parameters in Phase 3

### 4. Prompt Injection Risk
**Issue**: Simple sanitization may not be sufficient
**Impact**: Potential security vulnerability
**Status**: ✅ **IMPROVED** - Added system prompt with strict rules in Phase 3

### 5. No Hallucination Detection
**Issue**: No mechanism to detect when LLM hallucinates
**Impact**: May provide incorrect answers
**Recommendation**: Future enhancement - add answer grounding checks

---

## Scalability Concerns

### 1. In-Memory Cache
**Issue**: Cache size limited by container memory
**Impact**: May hit memory limits with high traffic
**Recommendation**: Use Redis or Memcached

### 2. No Connection Pooling
**Issue**: Postgres connections created per request
**Impact**: Connection overhead, potential exhaustion
**Recommendation**: Use psycopg2.pool

### 3. Synchronous Operations
**Issue**: All operations are synchronous
**Impact**: Blocking I/O limits throughput
**Recommendation**: Use async/await where possible

### 4. No Rate Limiting
**Issue**: No rate limiting on API endpoints
**Impact**: Vulnerable to abuse, DoS
**Recommendation**: Add rate limiting middleware

---

## Recommended Future Improvements

### High Priority
1. Replace in-memory cache with Redis
2. Add Postgres connection pooling
3. Add rate limiting middleware
4. Persist BM25 index to disk
5. Add authentication/authorization

### Medium Priority
1. Standardize logging across services
2. Add document-level summaries
3. Improve query routing (embedding-based)
4. Add answer grounding checks
5. Implement async operations

### Low Priority
1. Remove empty placeholder files
2. Consolidate configuration patterns
3. Add comprehensive integration tests
4. Add load testing
5. Implement secrets manager

---

## Summary

The repository has a functional architecture with some quality issues:
- **Dead Code**: Several empty placeholder files from intended modular architecture (no impact)
- **Duplicated Logic**: Minimal and appropriate (separate configs per service)
- **RAG Quality**: Improved with metrics, evaluation, and configurable parameters in Phase 3
- **Scalability**: Concerns around cache, connection pooling, and rate limiting
- **Observability**: Significantly improved with tracing, metrics, and diagnostics in Phase 3

Overall, the architecture is functional for local development and small-scale deployment. For production scaling, address the scalability concerns listed above.
