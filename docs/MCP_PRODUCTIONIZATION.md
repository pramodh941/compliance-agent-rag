# MCP Productionization Guide

This pass keeps the MCP server backward compatible with the existing local agent flow while making the service easier to run as a standalone production component.

## Architecture

The MCP server remains a small FastAPI service in `apps/mcp-server` with a clear split of responsibilities:

- `app.py` owns HTTP entrypoints, request tracing, auth enforcement, health endpoints, and timeout boundaries.
- `config.py` owns environment-driven runtime settings and deployment validation.
- `logging_utils.py` emits JSON logs with correlation IDs, tool names, status, transport, and duration fields.
- `tools.py` owns tool registration metadata, input validation, execution normalization, upstream retries, and calls into the compliance API.

The MCP layer is intentionally a tool facade. It should not own planner state, agent memory, or orchestration decisions. Those stay in `apps/agent-worker`.

## Current Tool Flow

Tools are registered in two compatible forms:

- FastMCP decorators in `app.py` preserve the existing MCP-oriented function surface.
- `TOOL_REGISTRY` in `tools.py` exposes explicit tool metadata, argument schema, allowlisted handlers, and normalized execution for HTTP clients.

The existing agent worker can keep calling `POST /mcp/{tool_name}` with the current payload shape. New external agents can discover tools through `GET /mcp/tools` and call the same execution endpoint with either a raw argument object or `{ "arguments": { ... } }`.

## Request Lifecycle

1. Client sends `POST /mcp/{tool_name}`.
2. Middleware assigns or propagates `X-Correlation-ID`, validates payload size, and logs request start.
3. Optional API-key auth runs when `MCP_AUTH_MODE=api-key`.
4. The request body is decoded and normalized into tool arguments.
5. `validate_tool_arguments` checks the tool allowlist, required args, unexpected args, value types, emptiness, and max string length.
6. `execute_tool` runs in a worker thread behind `asyncio.wait_for`.
7. Upstream API-backed tools use bounded `requests` timeouts and retry connection/timeout failures.
8. The response is returned as:

```json
{
  "result": {
    "tool": "rag_search",
    "status": "success",
    "duration_ms": 123.45,
    "structured_content": {}
  }
}
```

9. Completion logs include correlation ID, tool, status, transport, and duration.

## Entrypoints And Health

- `GET /health`: lightweight service health and config warnings.
- `GET /live`: liveness probe for container platforms.
- `GET /ready`: readiness probe that validates config and checks the compliance API `/health`.
- `GET /mcp/tools`: tool discovery metadata for agents.
- `POST /mcp/{tool_name}`: backward-compatible tool invocation endpoint.

Cloud Run compatibility is handled by the Dockerfile honoring `$PORT`:

```sh
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8001}
```

## Configuration

Important MCP settings:

- `API_BASE_URL`: compliance API base URL.
- `PORT` or `MCP_PORT`: server port. Cloud Run injects `PORT`.
- `LOG_LEVEL`: JSON log level.
- `MCP_AUTH_MODE`: `off` by default for local compatibility, `api-key` for production.
- `MCP_API_KEY`: required when `MCP_AUTH_MODE=api-key`.
- `MCP_TOOL_TIMEOUT`: max tool execution time.
- `API_REQUEST_TIMEOUT`: upstream API request timeout.
- `MCP_MAX_PAYLOAD_BYTES`: request body limit.
- `MCP_MAX_TEXT_CHARS`: per-string argument limit.
- `MCP_CORS_ORIGINS`: comma-separated allowed origins.
- `MCP_ALLOWED_TRANSPORTS`: currently documents the supported HTTP compatibility transport.

Recommended production auth baseline:

```sh
MCP_AUTH_MODE=api-key
MCP_API_KEY=<secret-from-secret-manager>
MCP_CORS_ORIGINS=https://your-agent-host.example
MCP_EXPOSE_ERROR_DETAILS=false
```

For stronger production isolation, place the service behind Cloud Run IAM, an API gateway, or service-to-service identity, and keep API-key auth as an application-level fallback.

## Local Testing

Start the current local stack:

```sh
docker compose up --build mcp-server api
```

Check health:

```sh
curl http://localhost:8001/health
curl http://localhost:8001/ready
```

Discover tools:

```sh
curl http://localhost:8001/mcp/tools
```

Invoke a local-only tool:

```sh
curl -X POST http://localhost:8001/mcp/analyze_text \
  -H "Content-Type: application/json" \
  -d '{"text":"confidential restricted information"}'
```

Invoke using the external-agent friendly shape:

```sh
curl -X POST http://localhost:8001/mcp/analyze_text \
  -H "Content-Type: application/json" \
  -d '{"arguments":{"text":"confidential restricted information"}}'
```

Run focused tests:

```sh
python tests/test_mcp_server.py
```

## Cloud Run Deployment

Build and push:

```sh
gcloud builds submit apps/mcp-server \
  --tag us-central1-docker.pkg.dev/PROJECT_ID/compliance/mcp-server:latest
```

Deploy:

```sh
gcloud run deploy compliance-mcp \
  --image us-central1-docker.pkg.dev/PROJECT_ID/compliance/mcp-server:latest \
  --region us-central1 \
  --allow-unauthenticated=false \
  --set-env-vars DEPLOYMENT_PROFILE=cloud-production,API_BASE_URL=https://COMPLIANCE_API_URL,MCP_AUTH_MODE=api-key,MCP_CORS_ORIGINS=https://YOUR_AGENT_HOST \
  --set-secrets MCP_API_KEY=mcp-api-key:latest
```

Operational recommendations:

- Use Cloud Run IAM for service-to-service access.
- Store `MCP_API_KEY` in Secret Manager.
- Set min instances if cold starts are unacceptable for agent workflows.
- Configure request timeout at or above `MCP_TOOL_TIMEOUT`.
- Route readiness checks to `/ready` and liveness checks to `/live`.
- Export JSON logs to Cloud Logging and alert on `status=error`, `status=timeout`, and readiness failures.

## Interoperability Validation

External agents should validate these assumptions before integration:

- `GET /mcp/tools` returns tool names, descriptions, and JSON-schema-like input metadata.
- `POST /mcp/{tool_name}` accepts both raw argument objects and `{ "arguments": ... }`.
- Responses include a stable `result.structured_content` object.
- Validation failures return `422`.
- Unknown tools return `422`.
- Tool timeouts return `504`.
- Upstream execution failures return `502` unless the tool implements a graceful fallback result.
- `X-Correlation-ID` is echoed and appears in server logs.

With auth enabled:

```sh
curl -H "X-API-Key: $MCP_API_KEY" https://MCP_URL/mcp/tools
curl -H "Authorization: Bearer $MCP_API_KEY" https://MCP_URL/mcp/tools
```

## Coupling And Scaling Notes

Current MCP/API coupling is synchronous and endpoint-oriented. That keeps local development simple, but future scaling should consider:

- Moving long-running tools to async jobs with a submitted/running/completed lifecycle.
- Adding a queue for expensive scans or multi-document workflows.
- Recording tool invocation audit events with correlation ID, agent ID, tool name, arguments hash, status, and duration.
- Adding per-agent rate limits and quotas once multiple external agents integrate.
- Separating public tool schemas from internal handler implementation details.
- Versioning tool names or metadata when schemas change, for example `rag_search.v2`.
- Adding transport adapters if true MCP stdio, SSE, or streamable HTTP support is required by a client.
- Using `httpx.AsyncClient` or a shared async upstream client if API-backed tools become high concurrency.
- Splitting CPU-heavy local tools into workers so the MCP process remains responsive.

The near-term architecture is ready for multiple agents because tool registration is explicit, execution is allowlisted and bounded, responses are normalized, and orchestration remains outside the MCP server.
