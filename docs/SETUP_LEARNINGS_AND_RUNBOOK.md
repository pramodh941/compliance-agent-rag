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

# Embedding Ingestion & Qdrant Debugging Learnings

## Problem Observed

Qdrant collection showed:

```json
{
  "points_count": 45,
  "indexed_vectors_count": 0
}
```

This meant points existed in Qdrant but vectors were not properly indexed, causing semantic/vector search failures.

---

# Root Causes Identified

## 1. Missing Embedding Validation

The Ollama embedding response was being trusted without validation.

Potential issues:
- missing `"embedding"` field
- `None` embeddings
- wrong vector dimensions
- malformed/non-numeric vectors

---

## 2. Invalid Vectors Reaching Qdrant

The ingestion pipeline inserted vectors into Qdrant without validating:
- vector exists
- vector length is correct
- values are numeric

This allowed corrupted vectors to reach storage.

---

## 3. Critical Bug in `sec_ingestion_service.py`

Old logic:

```python
vectors = [get_embedding(c) for c in all_chunks]
```

If embedding generation failed:

```python
[vec1, None, vec3, None]
```

These `None` vectors were uploaded to Qdrant.

Result:
- points created
- vectors not indexed
- `indexed_vectors_count = 0`

Fixed by:
- explicit loop
- filtering `None`
- validating vectors before upload

---

# Fixes Implemented

## `ollama_client.py`

Added:
- embedding response validation
- dimension checks
- numeric value checks
- structured logging
- improved error handling

Validation checks:
- embedding field exists
- embedding is a list
- expected dimension count
- numeric values only

---

## `policy_indexer.py`

Added:
- per-vector validation
- embedding failure tracking
- validation failure tracking
- detailed logging
- post-upload Qdrant verification

---

## `sec_ingestion_service.py`

Fixed:
- removed unsafe list comprehension
- added filtering for failed embeddings
- added validation before upload

---

## `main.py`

Added centralized logging configuration for ingestion/debug visibility.

---

# Key Debugging Insight

If Qdrant shows:

```json
points_count > 0
indexed_vectors_count = 0
```

then:
- ingestion partially succeeded,
- but vectors are malformed/missing/not indexed.

Always verify both counts.

---

# Important Validation Rules

Before uploading vectors to Qdrant:

- vector must not be `None`
- vector must be a list
- vector length must match embedding model dimensions
- all values must be numeric

---

# Useful Debug Commands

## Rebuild Containers

```bash
docker compose down
docker compose up -d --build
```

---

## Check API Logs

```bash
docker logs -f compliance-api
```

---

## Verify Qdrant Collection

```bash
curl http://localhost:6333/collections/policies
```

Check:

```json
indexed_vectors_count == points_count
```

---

## Trigger Policy Indexing

```bash
curl -X POST http://localhost:8000/index-policies
```

---

# Operational Learnings

- Validate embeddings at the source.
- Never trust external model responses blindly.
- Add logging around every ingestion stage.
- Validate vectors before database insertion.
- Track failure counts explicitly.
- Qdrant collection stats are critical for debugging ingestion issues.
- Silent embedding failures can appear as successful ingestion.

---

# Final Outcome

After fixes:
- vectors uploaded correctly
- `indexed_vectors_count` matched `points_count`
- semantic retrieval pipeline restored
- ingestion debugging visibility significantly improved

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

# 🚀 Agent Runtime Stabilization (LangGraph Loop Controls)

## ✅ Major Runtime Improvements

The agent runtime was stabilized to reduce hallucinations, infinite loops, and excessive planner calls.

---

## 🧠 Hybrid Routing Architecture

The system now uses:

Deterministic Router
→ Agent Planner (fallback only)
→ Tool Execution
→ Reflection
→ Conditional Continuation

Instead of routing every request through the LLM planner.

---

## ✅ Deterministic Intent Routing Added

Simple requests now bypass the planner entirely:

| Query Type | Route |
|---|---|
| policy lookup | rag_search |
| compliance scan | compliance_scan |
| suspicious/risk analysis | analyze_text |
| greetings | direct final_answer |

### Benefits
- lower latency
- reduced hallucinations
- fewer Ollama calls
- improved runtime predictability

---

## 🔴 Issue Fixed: Infinite LangGraph Recursion

### Symptoms

```text
GraphRecursionError
Recursion limit reached

Root Cause

final_answer responses were not treated as terminal states.

The graph continued cycling:

planner
→ tool_executor
→ reflection
→ planner

indefinitely.

Fix

Added:

explicit END conditions
terminal state handling
reflection-based stop logic
✅ Reflection Loop Improvements

Reflection node now:

stops on successful tool output
terminates on final_answer
detects repeated tool loops
prevents unnecessary replanning
📈 Result

The runtime behavior is now significantly more stable:

Area	Status
planner spam	reduced
infinite loops	fixed
repeated tool execution	fixed
greeting recursion	fixed
latency	improved
🧠 Key Learning

Production-grade agents should NOT rely entirely on autonomous LLM reasoning.

A hybrid approach works far better:

deterministic routing for obvious intents
LLM orchestration for ambiguous tasks
strict loop controls
reflection-based termination


🧠 Session Update: Stateful Agent Memory + Runtime Stabilization
✅ Major Architectural Milestone

The agent runtime evolved from:

stateless request routing

to:

stateful agent orchestration

The system now maintains session-scoped conversational memory across agent executions.

🚀 What Was Implemented
1. Session-Based Memory Layer

Added lightweight in-memory session persistence:

File added:

agents/memory.py

Capabilities:

store conversation history
retrieve prior interactions
persist responses across requests
clear session memory

Current implementation uses:

in-memory Python dictionary

Design intentionally kept simple for future migration to:

Redis
Postgres
Vector memory
Cloud memory services
2. Conversation History in Agent State

AgentState expanded to include:

session_id
conversation_history

This enables:

stateful orchestration
multi-turn workflows
conversational continuity
context-aware planning
3. Memory Injection into Planner

Planner now receives:

prior user requests
prior agent responses
previous workflow context

through:

conversation_history

Injected into planner prompt dynamically.

4. Structured Planner Validation Improvements

Planner outputs now validated using Pydantic:

PlannerResponse

Added:

strict tool name validation via Literal
structured argument enforcement

This prevents:

hallucinated tool execution
invalid planner outputs
unsafe orchestration behavior
5. Safe Planner Failure Handling

Previous behavior:

planner failure → ping tool fallback

New behavior:

planner failure → safe final_answer termination

This is important for:

governance
auditability
enterprise safety controls
6. LangGraph Runtime Stabilization

Fixed several orchestration issues:

Infinite recursion bug

Cause:

graph lacked proper stop condition handling for final_answer

Fix:

explicit graph termination logic
conditional edge stabilization
Repeated tool execution loops

Cause:

planner repeatedly selecting same tool

Fix:

reflection-based repeated-tool detection
Excessive LLM calls

Cause:

greetings/simple requests unnecessarily routed through planner LLM

Fix:

deterministic router fast-path

Examples:

greetings
simple policy lookups
direct analysis requests
🧪 Memory Validation Test

Validated session continuity using:

Request 1
find insider trading policy
Request 2
summarize it

Observed:

conversation history persisted correctly
planner received previous interaction context

Limitation:

lightweight model (gemma:2b) still weak at conversational inference

Important distinction:

Memory architecture works correctly.
Reasoning quality remains model-limited.
🏗️ Current Runtime Architecture
User Request
    ↓
Session Memory Load
    ↓
Deterministic Router
    ↓
Planner
    ↓
Tool Validation
    ↓
MCP Tool Execution
    ↓
Reflection Layer
    ↓
Memory Persistence
    ↓
Final Response
🔍 Key Learnings
Stateful orchestration is foundational

Memory transforms the system from:

stateless API orchestration

to:

conversational agent runtime
Deterministic routing is critical

Fast-path routing:

reduces latency
avoids unnecessary LLM calls
improves stability
lowers compute cost

Production systems heavily rely on hybrid:

deterministic routing
agentic reasoning
Lightweight local models have orchestration limits

gemma:2b works for:

tool routing
simple orchestration

But struggles with:

semantic continuation
conversational inference
multi-step reasoning

Architecture remains correct despite model limitations.

⚠️ Current Limitations
Memory is in-process only
resets on container restart
No semantic memory retrieval yet
No long-term memory storage
No summarization/compression layer
Planner still lacks confidence scoring
Reflection remains heuristic-based
🚀 Recommended Next Steps
Near-term
structured tool metadata registry
memory-aware routing
reflection scoring
response confidence estimation
Mid-term
Redis-backed memory
semantic memory retrieval
RAGAS evaluation
observability/tracing
Long-term
multi-agent orchestration
human approval workflows
cloud-native deployment
managed MCP integration
long-term vector memory
💡 Important Architectural Insight

The project has now evolved through several stages:

Basic RAG QA
    ↓
Hybrid Retrieval
    ↓
Compliance Detection
    ↓
MCP Tool System
    ↓
LangGraph Agent Runtime
    ↓
Stateful Agent Orchestration

This is now approaching the architecture style used in production-grade AI agent platforms.