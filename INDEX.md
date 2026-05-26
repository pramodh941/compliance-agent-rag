# Compliance Agent RAG Documentation Index

Last updated: May 9, 2026

This repository previously contained several phase-planning documents that described incomplete wiring. Those phase documents have been removed because the implementation has moved past them. Use the documents below as the current source of truth.

## Current Documents

| Document | Purpose |
| --- | --- |
| [README.md](README.md) | Minimal quick start. |
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | High-level project state, what is implemented, and remaining risks. |
| [STATUS_REPORT.md](STATUS_REPORT.md) | Current validated service status and phase-by-phase validation results. |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Developer commands, curl checks, and debugging reference. |
| [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md) | Current architecture, component responsibilities, and known technical debt. |
| [ARCHITECTURE_DIAGRAMS.md](ARCHITECTURE_DIAGRAMS.md) | Current runtime/data-flow diagrams. |
| [docs/ADK_A2A_INTEROPERABILITY.md](docs/ADK_A2A_INTEROPERABILITY.md) | Phase 7 ADK metadata, A2A card/endpoints, validation, and deployment guidance. |
| [docs/SETUP_LEARNINGS_AND_RUNBOOK.md](docs/SETUP_LEARNINGS_AND_RUNBOOK.md) | Operational runbook for WSL/Docker testing and troubleshooting. |

## Removed Documents

The following generated phase documents were deleted because they were stale after implementation and validation:

- `PHASE1_CHECKLIST.md`
- `PHASE1_COMPLETE.md`
- `PHASE2_PLANNING.md`

Their useful content is now consolidated into `STATUS_REPORT.md`, `QUICK_REFERENCE.md`, and `docs/SETUP_LEARNINGS_AND_RUNBOOK.md`.

## Validated Flow

```text
User curl/API request
-> FastAPI /agents/run
-> agent-worker LangGraph planner
-> MCP /mcp/rag_search
-> FastAPI /qa
-> Qdrant + BM25 + reranker + Ollama
-> source-backed answer
-> session persisted in Postgres
```

## Recommended Reading Order

1. Read `EXECUTIVE_SUMMARY.md` for context.
2. Use `docs/SETUP_LEARNINGS_AND_RUNBOOK.md` to run the stack.
3. Use `QUICK_REFERENCE.md` while testing or debugging.
4. Use `ARCHITECTURE_ANALYSIS.md` and `ARCHITECTURE_DIAGRAMS.md` for implementation context.
