# ADK and A2A Interoperability

Phase 7 adds lightweight interoperability around the existing compliance agent. The core architecture is unchanged:

```text
External agent or API client
-> A2A JSON-RPC or existing REST endpoint
-> agent-worker FastAPI adapter
-> existing LangGraph agent
-> existing MCP client
-> compliance-mcp tools
-> API/RAG/compliance services
```

The integration is additive. LangGraph remains the orchestration runtime, MCP remains the tool boundary, and the new ADK/A2A files describe or adapt the current agent instead of replacing it.

## New Surfaces

Agent worker:

| Endpoint | Purpose |
| --- | --- |
| `GET /.well-known/agent.json` | A2A-style discovery card alias. |
| `GET /.well-known/agent-card.json` | Machine-readable A2A agent card. |
| `GET /adk/agent` | ADK-compatible metadata for the LangGraph-backed agent. |
| `POST /a2a` | Minimal JSON-RPC A2A message endpoint. |
| `POST /run` | Existing agent execution contract, preserved. |

API service proxy:

| Endpoint | Purpose |
| --- | --- |
| `GET /agents/card` | Fetches the worker agent card. |
| `GET /agents/adk` | Fetches ADK-compatible metadata. |
| `POST /agents/a2a` | Proxies JSON-RPC A2A messages to agent-worker. |
| `POST /agents/run` | Existing API contract, preserved. |

Set `AGENT_PUBLIC_URL` to the externally reachable agent-worker URL so generated cards advertise a usable A2A endpoint. In local Docker Compose this defaults to `http://localhost:8002`.

## Implementation Files

| File | Responsibility |
| --- | --- |
| `apps/agent-worker/agents/runtime.py` | Reusable entrypoint for invoking the existing LangGraph agent. |
| `apps/agent-worker/agents/interop_skills.py` | Shared skill and workflow definitions. |
| `apps/agent-worker/agents/interop_metadata.py` | Agent card and ADK-compatible metadata builders. |
| `apps/agent-worker/agents/a2a_adapter.py` | JSON-RPC A2A request wrapper. |
| `apps/agent-worker/app/main.py` | Worker endpoints for cards, ADK metadata, A2A, and existing `/run`. |
| `apps/api/app/routes/agents.py` | API proxy endpoints for discovery and A2A. |
| `tests/test_phase7_interop.py` | Metadata and skill contract tests. |

## Workflow Mapping

| Workflow | ADK Skill ID | A2A Skill ID | MCP Tools | Notes |
| --- | --- | --- | --- | --- |
| Policy lookup | `policy_lookup` | `policy_lookup` | `rag_search` | Uses current RAG path through MCP. |
| Compliance risk analysis | `compliance_risk_analysis` | `compliance_risk_analysis` | `analyze_text`, `compliance_scan` | Supports text analysis or email ID analysis. |
| SEC regulation explanation | `sec_regulation_explanation` | `sec_regulation_explanation` | `rag_search` | Frames the user query as an SEC explanation task. |
| Escalation recommendation | `escalation_recommendation` | `escalation_recommendation` | `analyze_text`, `rag_search` | Keeps recommendation logic in the current agent/tool loop. |

## Interoperability Boundaries

MCP is still the only tool execution boundary. ADK metadata and A2A calls do not duplicate MCP tools; they advertise workflows and route execution back through the LangGraph agent, which then calls MCP as before.

A2A support is intentionally small: it accepts JSON-RPC 2.0 `message/send` and `tasks/send` requests at `/a2a`, extracts text or JSON payload metadata, maps the selected `skill_id` to a workflow prompt, and returns a JSON-RPC response with a data part. Streaming, push notifications, task polling, and auth negotiation are declared unsupported in the card.

ADK compatibility is metadata-oriented for now. The `/adk/agent` payload describes the agent instruction, runtime entrypoint, available skills, MCP tool mappings, and agent card. It is JSON serializable and transport agnostic so future ADK code can consume it without coupling this repository to ADK packages.

## Local Testing

Run unit checks:

```bash
python -m pytest tests/test_phase7_interop.py tests/test_mcp_server.py
python -m py_compile apps/agent-worker/app/main.py apps/agent-worker/agents/runtime.py apps/agent-worker/agents/interop_skills.py apps/agent-worker/agents/interop_metadata.py apps/agent-worker/agents/a2a_adapter.py
```

Run the stack:

```bash
docker compose up -d api mcp-server agent-worker postgres qdrant ollama
```

Validate discovery:

```bash
curl http://localhost:8002/.well-known/agent-card.json
curl http://localhost:8002/adk/agent
curl http://localhost:8000/agents/card
curl http://localhost:8000/agents/adk
```

## A2A Communication Validation

Send a policy lookup request directly to agent-worker:

```bash
curl -X POST http://localhost:8002/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "phase7-policy-lookup",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "text", "text": "Find the policy for restricted information handling."}
        ],
        "metadata": {
          "skill_id": "policy_lookup",
          "session_id": "phase7-local"
        }
      }
    }
  }'
```

The response should be a JSON-RPC object with `result.kind = "message"` and a data part containing `answer`, `observations`, and `errors`.

Validate through the API proxy:

```bash
curl -X POST http://localhost:8000/agents/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "phase7-sec",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {"kind": "text", "text": "Explain SEC Reg FD in plain language."}
        ],
        "metadata": {
          "skill_id": "sec_regulation_explanation",
          "session_id": "phase7-api"
        }
      }
    }
  }'
```

## MCP Interoperability Validation

Confirm the MCP registry still advertises the underlying tools:

```bash
curl http://localhost:8001/mcp/tools
```

Then run a direct MCP tool call:

```bash
curl -X POST http://localhost:8001/mcp/analyze_text \
  -H "Content-Type: application/json" \
  -d '{"text": "confidential restricted memo"}'
```

The A2A and ADK metadata should map back to these MCP tool names. No separate ADK or A2A tool implementation should be needed for normal operation.

## Cloud Run Deployment

Build and deploy the existing services as separate Cloud Run services. Use the same service boundaries already present in Docker Compose.

```bash
gcloud builds submit apps/api --tag REGION-docker.pkg.dev/PROJECT/REPO/compliance-api:phase7
gcloud builds submit apps/mcp-server --tag REGION-docker.pkg.dev/PROJECT/REPO/compliance-mcp:phase7
gcloud builds submit apps/agent-worker --tag REGION-docker.pkg.dev/PROJECT/REPO/compliance-agent-worker:phase7
```

Deploy MCP first, then agent-worker, then API:

```bash
gcloud run deploy compliance-mcp \
  --image REGION-docker.pkg.dev/PROJECT/REPO/compliance-mcp:phase7 \
  --region REGION \
  --set-env-vars API_BASE_URL=https://COMPLIANCE_API_URL

gcloud run deploy compliance-agent-worker \
  --image REGION-docker.pkg.dev/PROJECT/REPO/compliance-agent-worker:phase7 \
  --region REGION \
  --set-env-vars MCP_BASE_URL=https://COMPLIANCE_MCP_URL,AGENT_PUBLIC_URL=https://COMPLIANCE_AGENT_WORKER_URL

gcloud run deploy compliance-api \
  --image REGION-docker.pkg.dev/PROJECT/REPO/compliance-api:phase7 \
  --region REGION \
  --set-env-vars AGENT_WORKER_URL=https://COMPLIANCE_AGENT_WORKER_URL
```

Add the existing database, Qdrant, Ollama/model, and secret settings for the selected deployment profile. For production, keep MCP authentication enabled and pass credentials through headers at the transport layer.

Post-deploy checks:

```bash
curl https://COMPLIANCE_AGENT_WORKER_URL/.well-known/agent-card.json
curl https://COMPLIANCE_AGENT_WORKER_URL/adk/agent
curl https://COMPLIANCE_API_URL/agents/card
```

## Example External Agent Flow

1. External agent discovers `https://COMPLIANCE_AGENT_WORKER_URL/.well-known/agent-card.json`.
2. It selects `sec_regulation_explanation` from the `skills` list.
3. It sends a JSON-RPC 2.0 `message/send` request to the card `url`.
4. The A2A adapter maps the request to a workflow prompt.
5. The existing LangGraph agent plans and executes through MCP.
6. The external agent receives a JSON-RPC response containing the answer and tool observations.

## Future Extension Points

Add new workflows by adding one `InteropSkill` in `interop_skills.py` and, if needed, a targeted prompt branch in `build_workflow_prompt`. If the workflow needs a new capability, add it first as an MCP tool, then map the skill to that MCP tool.

Streaming can be added later by extending `/a2a` with server-sent events and setting `capabilities.streaming = true`. Task polling can be added with persistent task records. ADK package integration can consume `/adk/agent` or replace the metadata builder with official ADK objects while keeping the existing runtime entrypoint.
