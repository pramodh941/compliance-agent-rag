## Quick Start

1. docker compose up -d
2. Pull Ollama models
3. Run ingestion + indexing
4. Use /qa endpoint

See docs/SETUP_LEARNINGS_AND_RUNBOOK.md for full details

## Agent Interoperability

Phase 7 adds lightweight ADK-compatible metadata and A2A-compatible discovery/message endpoints around the existing LangGraph + MCP agent path.

- Agent card: `GET http://localhost:8002/.well-known/agent-card.json`
- ADK metadata: `GET http://localhost:8002/adk/agent`
- A2A JSON-RPC endpoint: `POST http://localhost:8002/a2a`
- API proxies: `GET /agents/card`, `GET /agents/adk`, `POST /agents/a2a`

See docs/ADK_A2A_INTEROPERABILITY.md for architecture, workflow mapping, validation, and Cloud Run steps.
