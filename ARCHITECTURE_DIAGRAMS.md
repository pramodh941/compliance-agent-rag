# Compliance Agent RAG - Architecture Diagrams

Last updated: May 9, 2026

## Service Topology

```mermaid
flowchart TD
    Client["Client / curl / UI"]
    API["FastAPI API :8000"]
    AgentService["agent_service.py"]
    Agent["Agent Worker :8002"]
    Graph["LangGraph planner/tool/reflection"]
    MCP["MCP Server :8001"]
    RAG["API /qa RAG service"]
    Qdrant["Qdrant :6333"]
    Ollama["Ollama :11434"]
    Reranker["Reranker :7997"]
    Postgres["Postgres :5432"]

    Client --> API
    API --> AgentService
    AgentService --> Agent
    Agent --> Graph
    Graph --> MCP
    MCP --> RAG
    RAG --> Qdrant
    RAG --> Reranker
    RAG --> Ollama
    Agent --> Postgres
    API --> Postgres
```

## Full Agent RAG Sequence

```mermaid
sequenceDiagram
    participant C as Client
    participant API as API :8000
    participant AW as Agent Worker :8002
    participant MCP as MCP Server :8001
    participant RAG as API /qa
    participant DB as Postgres

    C->>API: POST /agents/run
    API->>AW: POST /run
    AW->>AW: Plan tool call
    AW->>MCP: POST /mcp/rag_search
    MCP->>RAG: POST /qa
    RAG-->>MCP: Answer + sources
    MCP-->>AW: Tool result
    AW->>DB: Persist session memory
    AW-->>API: Agent result
    API-->>C: Normalized response
```

## Persistence Flow

```mermaid
flowchart LR
    EmailsJson["app/data/emails.json seed data"]
    Ingest["POST /ingest"]
    EmailRepo["email_repo.py"]
    RuleEngine["rule_engine.py"]
    EmailsTable["emails table"]
    AlertsTable["alerts table"]
    SessionsTable["sessions table"]
    AgentRun["POST /agents/run"]

    EmailsJson --> Ingest
    Ingest --> EmailRepo
    EmailRepo --> EmailsTable
    Ingest --> RuleEngine
    RuleEngine --> AlertsTable
    AgentRun --> SessionsTable
```

## Report Flow

```mermaid
flowchart TD
    Request["GET /reports/compliance-summary"]
    Repo["list_emails()"]
    Rules["evaluate_rules()"]
    Summary["alerts_by_rule + totals"]

    Request --> Repo
    Repo --> Rules
    Rules --> Summary
```

## Key Ports

| Service | Port |
| --- | --- |
| API | 8000 |
| MCP server | 8001 |
| Agent worker | 8002 |
| Postgres | 5432 |
| Qdrant | 6333 |
| Reranker | 7997 |
| Ollama | 11434 |
