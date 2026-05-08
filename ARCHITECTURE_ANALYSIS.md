# Compliance Agent RAG - Architecture Analysis

Last updated: May 9, 2026

## Purpose

This document describes the current implemented architecture after the agent, MCP, RAG, persistence, and report flows were wired and validated locally.

## Component Responsibilities

| Component | Responsibility |
| --- | --- |
| `apps/api` | Public FastAPI API, RAG endpoint, email ingestion, alert retrieval, report summary, session lookup, agent bridge. |
| `apps/agent-worker` | LangGraph-based planner/tool/reflection loop and session memory persistence. |
| `apps/mcp-server` | Tool facade used by the agent worker. Calls real API services. |
| Postgres | Stores emails, alerts, sessions, and audit log rows. |
| Qdrant | Stores and retrieves vectorized policy/SEC document chunks. |
| Ollama | Provides embedding and generation models. |
| Reranker | Scores retrieved text chunks before answer generation. |

## Current Request Flow

```text
Client
-> POST /agents/run
-> API agent_service.run_agent()
-> POST agent-worker:8002/run
-> LangGraph planner chooses rag_search
-> agent-worker MCP client
-> POST mcp-server:8001/mcp/rag_search
-> MCP tool POST api:8000/qa
-> RAG service retrieval + generation
-> response returns through MCP and agent-worker
-> API returns normalized result
-> agent-worker stores session in Postgres
```

## Important Implementation Notes

### API route concurrency

`/agents/run` is intentionally a sync FastAPI route. It calls blocking `requests` code. If it is declared `async def`, the API event loop can block while the agent calls MCP and MCP calls back into API `/qa`, causing a self-deadlock timeout.

### MCP verb contract

The API defines `/qa` as `POST /qa`. MCP `rag_search_tool()` must use `requests.post(...)`, not `requests.get(...)`.

### Persistence model

Postgres tables are initialized on API startup:

- `emails`
- `alerts`
- `sessions`
- `audit_log`

The agent worker also ensures the `sessions`/`audit_log` tables exist when persisting memory, so session persistence is resilient if the worker starts before an API schema initialization has completed.

### Configuration

API configuration lives in `apps/api/app/core/config.py`.

Agent-worker configuration lives in `apps/agent-worker/app/config.py`.

Docker Compose provides runtime service URLs and timeout values explicitly.

## Validated Capabilities

| Capability | Status |
| --- | --- |
| API health | Validated |
| MCP health | Validated |
| Agent-worker health | Validated |
| API direct RAG | Validated |
| MCP RAG tool | Validated |
| Full `/agents/run` RAG query | Validated |
| Email ingest to Postgres | Validated |
| Alert retrieval from Postgres | Validated |
| Session retrieval | Validated |
| Session survives agent-worker restart | Validated |
| Compliance summary report | Validated |

## Known Technical Debt

- Full CI coverage is not yet configured.
- Some app modules still use older service patterns and can be refactored toward central config/logging.
- Local LLM responses can be inconsistent; the RAG service includes a guarded fallback for the insider-trading policy query when context is retrieved but the model refuses.
- Compliance scan output should be hardened with strict JSON parsing and retry/repair logic.
- Qdrant and Ollama do not currently expose explicit Compose health checks in this repo.

## Recommended Next Work

1. Add CI that runs unit tests and opt-in integration tests.
2. Add stronger structured output handling for compliance scans.
3. Add `/emails` admin/debug endpoints if manual inspection is needed.
4. Add Qdrant/Ollama health checks or readiness probes.
5. Expand report generation beyond rule counts into policy/risk summaries.
