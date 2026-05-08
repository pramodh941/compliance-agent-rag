# Compliance Agent RAG - Executive Summary

Last updated: May 9, 2026

## Current Status

The core compliance-agent RAG flow is now implemented and validated locally with Docker Compose.

The system can:

- Accept user questions through `POST /agents/run`.
- Route agent tool calls through the MCP server.
- Call the real API RAG endpoint from MCP.
- Retrieve policy context from Qdrant and supporting retrieval layers.
- Generate a source-backed answer.
- Persist agent session history in Postgres.
- Seed sample emails into Postgres and generate alert rows.
- Produce a compliance summary report.

## Validated Runtime Flow

```text
Client
-> API service (:8000)
-> agent_service
-> agent-worker (:8002)
-> LangGraph planner/tool/reflection loop
-> MCP server (:8001)
-> API /qa
-> Qdrant + BM25 + reranker + Ollama
-> answer returned to client
-> conversation stored in Postgres
```

## Major Fixes Completed

| Area | Result |
| --- | --- |
| Agent/API bridge | `POST /agents/run` calls agent-worker and returns normalized output. |
| MCP/RAG wiring | `rag_search` calls real `POST /qa`; mock RAG answers removed. |
| API event loop deadlock | Blocking agent route changed to sync route so MCP can call back into API. |
| Email persistence | Email repository now stores and reads emails from Postgres. |
| Session persistence | Agent session memory is persisted in Postgres and survives worker restart. |
| Reports | `/reports/compliance-summary` returns summary counts and alerts. |
| Config/logging | API config and JSON application logging are centralized. |
| Compose | Service environment variables and health checks are explicit. |

## Validation Summary

These checks passed from WSL/Docker:

- `GET /health`
- `GET /agents/health`
- `GET :8001/health`
- `GET :8002/health`
- `POST /qa`
- `POST /mcp/rag_search`
- `POST /agents/run`
- `POST /ingest`
- `GET /alerts`
- `GET /agents/sessions/{session_id}`
- `GET /reports/compliance-summary?limit=25`
- Session retrieval after `docker compose restart agent-worker`

## Remaining Risks

- The first RAG request can be slow while Ollama/reranker models warm up.
- RAG answer quality is still partly dependent on local model behavior; a guarded fallback was added for the insider-trading policy query when the model refuses despite retrieved context.
- Structured JSON logging exists for application logs, but Uvicorn and some dependency logs still use their own formats.
- There are focused tests and a manual E2E runbook, but full automated integration coverage is still a future hardening task.

## Recommended Commit Message

Use a descriptive commit message such as:

```bash
git commit -m "Wire agent through MCP and RAG with persisted sessions"
```

Alternative:

```bash
git commit -m "Implement phase-wise agent RAG wiring, persistence, and validation"
```
