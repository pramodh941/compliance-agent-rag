````md
# 🧠 Compliance Agent RAG — Architecture, Learnings & Runbook

---

# 📌 Overview

This document captures the major architectural decisions, debugging learnings, operational commands, and runtime observations discovered while building the Compliance Agent RAG platform using:

- FastAPI
- FastMCP
- LangGraph
- Ollama
- Qdrant
- Postgres
- Docker Compose

The system evolved from a basic RAG API into an autonomous agent-oriented compliance platform.

---

# 🚀 Major Architectural Evolution

The system transitioned from:

```text
deterministic workflow orchestration
````

to:

```text
autonomous agent orchestration
```

Old flow:

```text
classify → route → execute
```

Current flow:

```text
plan
→ tool execution
→ observation
→ reflection
→ continuation decision
```

This is the most important architectural shift in the project so far.

---

# 🧠 Current Runtime Architecture

```text
User/API
   ↓
FastAPI Agent Worker
   ↓
LangGraph Runtime
   ↓
LLM Planner (Ollama)
   ↓
Validated Tool Selection
   ↓
MCP HTTP Execution Layer
   ↓
Compliance / RAG Tools
```

---

# 🧩 Core Components

| Component      | Responsibility              |
| -------------- | --------------------------- |
| FastAPI        | External API layer          |
| LangGraph      | Agent orchestration runtime |
| Ollama         | Local planner LLM           |
| FastMCP        | Tool execution layer        |
| Qdrant         | Vector retrieval            |
| Postgres       | Persistence layer           |
| Docker Compose | Service orchestration       |

---

# 🐳 Docker Learnings

## Important Networking Rule

Inside containers:

```text
http://service-name:port
```

must be used instead of:

```text
localhost
```

Examples:

```text
http://mcp-server:8001
http://ollama:11434
```

---

## Useful Commands

### Start system

```bash
docker compose up -d
```

### Stop system

```bash
docker compose down
```

### Rebuild one service

```bash
docker compose build agent-worker
```

### View logs

```bash
docker compose logs -f agent-worker
docker compose logs -f ollama
```

### View running containers

```bash
docker ps
```

---

# 🧠 Ollama Learnings

## CPU-Friendly Model Choice

Current planner model:

```text
gemma:2b
```

Reason:

* lightweight
* CPU-friendly
* sufficient for tool orchestration

---

## Pull Required Models

```bash
docker exec -it compliance-ollama ollama pull gemma:2b
docker exec -it compliance-ollama ollama pull nomic-embed-text
```

---

## Verify Installed Models

```bash
curl http://localhost:11434/api/tags
```

---

## Important API Change

Older examples often use:

```text
/api/generate
```

Current Ollama versions use:

```text
/api/chat
```

Using `/api/generate` caused:

```text
404 Client Error
```

Fix:

```text
http://ollama:11434/api/chat
```

---

## Performance Observations (CPU Runtime)

Observed timings on CPU-only setup:

| Operation        | Approx Time     |
| ---------------- | --------------- |
| First model load | ~50 seconds     |
| Planner requests | ~30–40 seconds  |
| Embeddings       | relatively fast |
| Retrieval        | fast            |

This is expected for local CPU inference.

---

# 🧠 LangGraph Runtime Refactor

The graph was refactored from workflow routing into an autonomous loop.

Current structure:

```text
planner
→ tool_executor
→ reflection
→ planner (loop)
```

The runtime now supports:

* iterative reasoning
* observation tracking
* autonomous continuation
* loop termination controls
* tool-based orchestration

---

# 🧠 Agent State Evolution

`AgentState` now tracks:

* observations
* tool history
* iteration count
* final response
* continuation decisions
* tool outputs

Important fields:

```python
observations
tool_result
iteration_count
max_iterations
should_continue
```

The state acts as the shared cognition/memory surface for the runtime.

---

# 🔐 Tool Governance Layer

Added:

* tool registry
* execution validation
* argument validation

Files:

```text
agents/tool_registry.py
agents/validator.py
```

Purpose:

Prevent:

* hallucinated tools
* malformed execution plans
* invalid arguments
* unsafe execution behavior

This establishes the foundation for:

* policy enforcement
* execution governance
* audit logging
* auth systems
* approval workflows

---

# 🧠 Observation-Aware Planning

The planner now receives:

* previous observations
* prior tool outputs
* execution history

through:

```python
observations
```

This enables:

* iterative reasoning
* multi-step orchestration
* reflection-based continuation

---

# ⚠️ Current Agent Limitation

The agent currently tends to repeat the same tool call.

Example:

```text
compliance_scan
→ compliance_scan
→ compliance_scan
```

Reason:

* lightweight model limitations
* weak reflection heuristics
* no semantic evaluation yet
* no confidence scoring
* no stopping-quality evaluation

This is expected at the current stage.

---

# 🧠 Current Runtime Safeguards

Current protections include:

* max_iterations
* tool validation
* required argument validation
* controlled tool registry

These are critical to prevent:

* infinite loops
* uncontrolled orchestration
* hallucinated execution
* invalid tool usage

---

# 🧠 MCP Learnings

## Important Direction

The system moved away from:

```text
stdio-only MCP
```

toward:

```text
HTTP-based MCP
```

Reason:

* cloud deployable
* Docker/Kubernetes friendly
* scalable
* service-oriented architecture
* industry-aligned design

---

# 🧩 MCP Architecture

Current structure:

```text
Agent Worker
    ↓ HTTP
MCP Server
    ↓
Compliance / RAG Tools
```

Tool execution endpoint:

```text
POST /mcp/{tool_name}
```

---

# 🧠 RAG Pipeline Learnings

## Hybrid Retrieval

Implemented:

* dense retrieval (Qdrant)
* sparse retrieval (BM25)

Benefits:

* improved recall
* better keyword matching
* stronger retrieval coverage

---

## Retrieval Observations

### Vector-only retrieval

* fast
* semantically useful
* weaker on exact keywords

### BM25

* improves keyword-heavy compliance queries
* improves recall

### Reranker

* improves precision
* expensive on CPU
* should remain optional

---

# ⚠️ Reranker Learnings

Observed:

* high latency
* timeouts on CPU
* unstable local performance

Current design correctly falls back to original ranking if reranker fails.

This is important and should remain.

---

# 🧠 Caching Layer

Implemented lightweight TTL cache for:

* embeddings
* responses

Benefits:

* avoids duplicate computation
* improves repeated-query latency
* reduces local CPU pressure

Future direction:

* Redis
* distributed caching
* cache metrics

---

# 🗄️ Postgres Learnings

Current limitation:

* no migration framework yet

Tables must currently be created manually.

Example:

```sql
CREATE TABLE alerts (
  email_id TEXT,
  rule_type TEXT,
  message TEXT,
  PRIMARY KEY (email_id, rule_type, message)
);
```

---

# 📥 Ingestion Learnings

The pipeline only works correctly when ALL system state exists:

Required:

* containers running
* Ollama models installed
* Qdrant collections created
* Postgres tables created
* policies indexed
* ingestion completed

Missing any component often causes:

```text
500 errors
```

---

# 🧪 Important Operational Commands

## Start all services

```bash
docker compose up -d
```

---

## Pull Ollama models

```bash
docker exec -it compliance-ollama ollama pull gemma:2b
docker exec -it compliance-ollama ollama pull nomic-embed-text
```

---

## Index policies

```bash
curl -X POST http://localhost:8000/index-policies
```

---

## Run ingestion

```bash
curl -X POST http://localhost:8000/ingest
```

---

## Test agent worker

```bash
curl http://localhost:8002/health
```

---

## Test autonomous agent

```bash
curl -X POST http://localhost:8002/run \
-H "Content-Type: application/json" \
-d '{"input":"find insider trading policy"}'
```

---

# ⚡ Current System Status

## Working

* Docker Compose orchestration
* FastAPI services
* MCP HTTP transport
* LangGraph runtime
* Ollama planner integration
* autonomous planning loop
* tool validation
* hybrid retrieval
* caching
* compliance scan flow
* MCP tool execution

---

## Not Yet Implemented

* semantic reflection quality
* confidence scoring
* checkpoint persistence
* structured observability
* auth/security
* audit pipelines
* streaming responses
* cloud deployment manifests
* production retries/circuit breakers

---

# 🚀 Recommended Future Improvements

## Agent Runtime

* stronger reflection prompts
* semantic stopping criteria
* planner self-evaluation
* retry differentiation
* confidence scoring
* memory persistence

---

## Retrieval

* better embeddings
* improved chunking
* retrieval evaluation
* reranker optimization

---

## Infrastructure

* DB migrations
* structured logging
* tracing/metrics
* Redis cache
* async execution
* queue-based orchestration
* GCP deployment

---

# 💡 Key Takeaway

This system evolved from:

```text
basic RAG QA
```

to:

```text
hybrid retrieval
→ MCP tools
→ LangGraph orchestration
→ autonomous agent runtime
→ policy-driven compliance platform
```

The platform is now moving toward:

```text
agentic AI infrastructure
```

rather than a simple RAG application.

---

# Autonomous Runtime Reliability Improvements

## Added Reflection Layer

The agent now includes:

- reflection node
- repeated tool detection
- termination heuristics
- observation-aware continuation

Purpose:

Prevent:
- infinite loops
- repeated tool execution
- uncontrolled planning cycles

---

## Added Structured Output Parser

LLM outputs are unreliable and may include:

- markdown
- prose
- fenced JSON
- partial formatting

A robust parser was added to:

- extract JSON safely
- recover malformed responses
- support markdown-wrapped JSON

Key learning:

LLMs are probabilistic text generators, not guaranteed protocol generators.

Production agent systems require:

- parsers
- validators
- retries
- schema enforcement
- repair logic

---

## Planner Quality Observation

`gemma:2b` works for lightweight orchestration but has limitations:

- weak tool discrimination
- weak stopping behavior
- inconsistent instruction following

Observed examples:

- policy lookup routed incorrectly to `compliance_scan`
- verbose/non-JSON responses
- repeated tool preference

This is primarily a planner-model limitation rather than a runtime architecture issue.

---

## CPU Runtime Observation

Planner requests may timeout on CPU-only setups.

Observed:
- first model load extremely slow
- long LangGraph loops amplify latency

Mitigation:
- increased planner timeout to 300 seconds
- lightweight planner models preferred for local testing