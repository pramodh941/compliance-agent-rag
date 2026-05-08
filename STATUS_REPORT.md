# Compliance Agent RAG - Status Report

Last updated: May 9, 2026

## Overall Status

Status: functional local Docker Compose stack.

The implementation has moved beyond the original Phase 1/Phase 2 planning docs. Core wiring, persistence, report summary, and smoke validation are implemented.

## Service Status

| Service | Port | Status | Notes |
| --- | --- | --- | --- |
| API | 8000 | Working | Main FastAPI service. |
| MCP server | 8001 | Working | Exposes `rag_search`, `compliance_scan`, and supporting tools. |
| Agent worker | 8002 | Working | LangGraph planner/tool/reflection loop. |
| Postgres | 5432 | Working | Stores emails, alerts, sessions, audit logs. |
| Qdrant | 6333 | Working | Vector retrieval. |
| Ollama | 11434 | Working | Embeddings and generation. |
| Reranker | 7997 | Working | Cross-encoder reranking. |

## Phase Validation

### Phase 1: Core Wiring

Validated:

- API `/agents/run` calls the agent worker.
- Agent worker calls MCP.
- MCP calls the real API `/qa` endpoint.
- `/qa` performs RAG retrieval and returns source-backed context.
- Full agent response contains a real insider-trading policy answer.

Important fixes:

- MCP now calls `POST /qa` instead of `GET /qa`.
- API agent routes are sync routes, avoiding event-loop blocking during agent-to-MCP-to-API callbacks.
- MCP and agent-worker timeouts were increased for first-call model warmup.

### Phase 2: Persistence, Config, Logging

Validated:

- `POST /ingest` seeds 25 sample emails into Postgres.
- `GET /alerts` returns persisted alert rows.
- Agent sessions are stored in Postgres.
- Session data survives `docker compose restart agent-worker`.
- API config is centralized in `app/core/config.py`.
- Application logs use JSON formatting where controlled by app code.

### Phase 3: Reports

Validated:

- `GET /reports/compliance-summary?limit=25` returns:
  - `email_count: 25`
  - alert counts
  - alerts grouped by rule

### Phase 4: Tests

Implemented:

- `tests/test_phase_flows.py` with a pure report-generation unit test and opt-in E2E tests.

Validation note:

- The local Windows shell did not have `python`/`py` installed.
- The report unit check was run inside the `agent-worker` container.
- Full E2E assertions were run with PowerShell/curl-equivalent requests against the live stack.

### Phase 5: Compose Health

Validated:

- `docker compose ps` shows core services running, with health checks for API, MCP, agent-worker, Postgres, and reranker.
- Health endpoints return OK.

## Current Known Gaps

- Full automated CI is not configured.
- Qdrant and Ollama do not currently have explicit Compose health checks.
- Some logs from Uvicorn/dependencies remain non-JSON.
- Compliance scan output may be partial if the local model truncates JSON; it is usable but should be hardened before production use.

## Smoke Test Result

The WSL manual smoke tests passed:

- Health checks passed.
- RAG direct check passed.
- MCP RAG check passed.
- Full agent RAG check passed.
- Ingestion and alerts passed.
- Session persistence passed.
- Report summary passed.
