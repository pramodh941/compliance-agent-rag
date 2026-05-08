# Compliance Agent RAG - Quick Reference

Last updated: May 9, 2026

## Start From WSL

```bash
cd /home/cadee/projects/compliance-agent-rag

docker compose down
docker compose up -d --build
docker compose ps
```

## Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8000/agents/health
```

Expected:

```json
{"api":"ok","postgres":"ok","qdrant":"ok"}
{"status":"healthy"}
{"status":"ok"}
{"status":"healthy","agent_worker":"connected"}
```

## Phase 1: Agent RAG Flow

Direct API RAG:

```bash
curl -X POST "http://localhost:8000/qa?query=What%20is%20the%20insider%20trading%20policy%3F"
```

MCP RAG:

```bash
curl -X POST http://localhost:8001/mcp/rag_search \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the insider trading policy?"}'
```

Full agent flow:

```bash
curl -X POST http://localhost:8000/agents/run \
  -H "Content-Type: application/json" \
  -d '{"input":"What is the insider trading policy?","session_id":"manual-phase1"}'
```

Expected:

- Response has `status: success`.
- `observations` includes `rag_search`.
- Answer mentions material non-public information.
- Sources include MNPI/personal trading policy context.

## Phase 2: Persistence

Seed emails and alerts:

```bash
curl -X POST http://localhost:8000/ingest
curl http://localhost:8000/alerts
```

Expected:

- `/ingest` returns `email_count: 25`.
- `/alerts` returns persisted alert rows.

Validate persisted session:

```bash
curl http://localhost:8000/agents/sessions/manual-phase1
curl http://localhost:8000/agents/sessions
```

Restart worker and confirm the session remains:

```bash
docker compose restart agent-worker
sleep 10
curl http://localhost:8000/agents/sessions/manual-phase1
```

## Phase 3: Reports

```bash
curl "http://localhost:8000/reports/compliance-summary?limit=25"
```

Expected shape:

```json
{
  "status": "success",
  "email_count": 25,
  "alert_count": 5,
  "alerts_by_rule": {
    "MNPI": 2,
    "Channel Change": 2,
    "Gifts": 1
  }
}
```

## Compliance Scan Checks

```bash
curl -X POST "http://localhost:8000/scan-email?email_id=e1"
curl -X POST "http://localhost:8000/scan-email?email_id=e10"
curl -X POST "http://localhost:8000/scan-email?email_id=does-not-exist"
```

Expected:

- Valid IDs return `email_id`, `analysis`, and `context_used`.
- Invalid IDs return `{"error":"Email not found"}`.

## One-Shot Smoke Test

```bash
set -e

curl -f http://localhost:8000/health
curl -f http://localhost:8001/health
curl -f http://localhost:8002/health
curl -f http://localhost:8000/agents/health

curl -f -X POST http://localhost:8000/ingest

curl -f -X POST http://localhost:8000/agents/run \
  -H "Content-Type: application/json" \
  -d '{"input":"What is the insider trading policy?","session_id":"smoke-test"}'

curl -f "http://localhost:8000/reports/compliance-summary?limit=25"
curl -f http://localhost:8000/agents/sessions/smoke-test

echo "All smoke tests passed"
```

## Debugging

```bash
docker compose ps

docker compose logs --tail 100 api
docker compose logs --tail 100 mcp-server
docker compose logs --tail 100 agent-worker
docker compose logs --tail 100 postgres
docker compose logs --tail 100 reranker
docker compose logs --tail 100 ollama
```

## Common Issues

### MCP or Agent Times Out

First model calls can be slow. Re-run after warmup and inspect:

```bash
docker compose logs --tail 100 api
docker compose logs --tail 100 mcp-server
docker compose logs --tail 100 agent-worker
```

### Dependency Change Not Reflected

Rebuild images:

```bash
docker compose up -d --build
```

### Session Missing

Run an agent request first, then check the session:

```bash
curl -X POST http://localhost:8000/agents/run \
  -H "Content-Type: application/json" \
  -d '{"input":"What is the insider trading policy?","session_id":"debug-session"}'

curl http://localhost:8000/agents/sessions/debug-session
```
