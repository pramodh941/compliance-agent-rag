# 🧠 Compliance Agent RAG – Setup Learnings & Runbook

## 📌 Overview

This document captures the **real-world issues, debugging steps, fixes, and working commands** discovered while getting the system up and running locally using Docker, FastAPI, Ollama, Qdrant, and Postgres.

---

# 🚀 What Actually Matters (Reality Check)

Getting the system “up” is not enough. The pipeline only works when:

1. ✅ Containers are running
2. ✅ Models are pulled in Ollama
3. ✅ Qdrant collection exists
4. ✅ Postgres tables exist
5. ✅ Data is ingested + indexed

Missing *any one* of these → **500 errors guaranteed**

---

# 🐳 Docker Learnings (Critical)

## 🔴 Issue: Containers exiting randomly

Seen as:

```
Exited (137)
```

### ✅ Fix

```
docker compose down
docker compose up -d
```

---

## 🔴 Issue: Ollama container running but no models

Symptoms:

* `/api/embeddings` → 404

### ✅ Fix

```
docker exec -it compliance-ollama ollama pull nomic-embed-text
docker exec -it compliance-ollama ollama pull gemma:2b
```

### 🔍 Learning

Ollama does NOT auto-download models.

---

## 🔴 Issue: Services not reachable

### Debug commands

```
docker ps
docker logs <container_name>
```

---

# 🧠 RAG Pipeline Learnings

## 🔴 Issue: Qdrant collection not found

Error:

```
Collection `policies` doesn’t exist
```

### ✅ Fix

Run indexing:

```
curl -X POST http://localhost:8000/index-policies
```

---

## 🔴 Issue: QA endpoint returns 500

Root causes seen:

* Missing embeddings model
* Missing Qdrant collection

### ✅ Fix Order

1. Pull models
2. Start containers
3. Index policies
4. Then query

---

## 🔴 Issue: Model gives wrong answers despite correct context

Example:

* Context clearly says: "Do not use WhatsApp"
* Model says: "Not found"

### ✅ Fix

Improve prompt in `rag_service.py`

Add:

```
- Answer ONLY from context
- If answer exists, do NOT say 'not found'
- Be direct and explicit
```

### 🔍 Learning

Small models (gemma:2b) are weak at reasoning even with correct retrieval.

---

# 🗄️ Postgres Learnings

## 🔴 Issue: Table does not exist

Error:

```
relation "alerts" does not exist
```

### ✅ Fix

Create table manually:

```
docker exec -it compliance-postgres psql -U <your_user> -d <your_db>
```

Then:

```
CREATE TABLE alerts (
  email_id TEXT,
  rule_type TEXT,
  message TEXT,
  PRIMARY KEY (email_id, rule_type, message)
);
```

### 🔍 Learning

No migrations are set up yet → schema must be created manually.

---

# 📥 Ingestion Learnings

## 🔴 Issue: `/ingest` failing

Root cause:

* Missing DB table

### ✅ Fix

Create table → re-run ingestion

---

## ✅ Working command

```
curl -X POST http://localhost:8000/ingest
```

---

# 📚 Policy Indexing

## ✅ Working command

```
curl -X POST http://localhost:8000/index-policies
```

### What it does:

* Reads `policies.txt`
* Splits into chunks
* Generates embeddings via Ollama
* Stores in Qdrant

---

# ❓ QA Endpoint Usage

## ⚠️ Common mistake

Spaces in query break curl

### ❌ Wrong

```
...query=What is GDPR compliance?
```

### ✅ Correct

```
curl -X POST "http://localhost:8000/qa?query=What%20is%20GDPR%20compliance?"
```

---

# 🧪 Full Working Flow (Golden Path)

Run these in order:

### 1️⃣ Start system

```
docker compose up -d
```

### 2️⃣ Pull models (only first time)

```
docker exec -it compliance-ollama ollama pull nomic-embed-text
docker exec -it compliance-ollama ollama pull gemma:2b
```

### 3️⃣ Create DB table (one-time)

```
docker exec -it compliance-postgres psql -U <user> -d <db>
```

Run SQL:

```
CREATE TABLE alerts (...);
```

### 4️⃣ Run ingestion

```
curl -X POST http://localhost:8000/ingest
```

### 5️⃣ Index policies

```
curl -X POST http://localhost:8000/index-policies
```

### 6️⃣ Ask question

```
curl -X POST "http://localhost:8000/qa?query=Your%20question"
```

---

# ⚡ Performance Expectations

* Embeddings: fast (sub-second per chunk)
* Retrieval: fast
* Generation (gemma:2b CPU): 1–5 seconds

---

# 🧩 Current Limitations

1. ❌ No DB migrations
2. ❌ Weak LLM (poor reasoning)
3. ❌ No reranker integration yet
4. ❌ No structured prompts / guardrails
5. ❌ Scripts folder empty (manual ops required)

---

# 🚀 Suggested Next Improvements

* Add DB migration script
* Add ingestion script (non-API)
* Integrate reranker
* Upgrade model (Mixtral / Llama3 via GPU or cloud)
* Improve prompt templates

---

# 💡 Key Takeaway

This system is **pipeline-sensitive**:

> Retrieval, embeddings, DB, and model must ALL be correctly initialized.

Most failures were not code bugs — they were **missing system state**.

---

# 🏁 Status

✅ End-to-end pipeline working
✅ API functional
✅ RAG loop complete
⚠️ Answer quality limited by model

---

This document should save hours of debugging for anyone running this repo next time 🚀

---

# 🧪 Additional Real-World Learnings (Latest Session)

## 🔴 Issue: Ollama timeouts during embedding & generation (CPU setup)

### Symptoms

```
[embedding error] Read timed out
requests.exceptions.ReadTimeout (generate_response)
```

### ✅ Fix

* Increase timeout in `ollama_client.py`

  * Embedding: `timeout=30`
  * Generation: `timeout=120–300`

### 🔍 Learning

Running LLMs on CPU is **slow and unstable under load**.

* Embeddings during ingestion → many parallel calls → timeouts
* Generation → large prompt + context → slower response

👉 This is **expected**, not a bug.

---

## 🔴 Issue: Partial ingestion due to embedding failures

### Symptoms

* Some chunks fail with embedding timeout
* Still see ingestion complete

### 🔍 Learning

Your system currently:

* Continues ingestion even if some chunks fail
* Leads to **incomplete vector coverage**

👉 This explains weak retrieval sometimes.

---

## 🔴 Issue: Reranker timeouts

### Symptoms

```
[reranker error] Read timed out
```

### Current Behavior (Good Design 👍)

* System **falls back to original ranking**
* QA still works (no crash)

### 🔍 Learning

Reranker is:

* Helpful, but **non-critical dependency**
* Should always fail gracefully (which your system now does)

---

## 🧪 How to Stop Only Reranker Container

### Command

```
docker stop compliance-reranker
```

### Restart later

```
docker start compliance-reranker
```

### 🔍 Learning

This allows you to:

* Test baseline RAG (no reranking)
* Compare answer quality

---

## 🧠 Retrieval Observations

### 1. Routing Works ✅

* Policy queries → `policies`
* SEC queries → `sec_docs`
* Ambiguous → both

---

### 2. Retrieval Quality is OK but not perfect

Seen issues:

* Irrelevant chunks (especially SEC docs noise)
* Missing exact answers even when partially present

### 🔍 Learning

This is due to:

* Small embedding model (`nomic-embed-text`)
* Limited chunk quality
* No semantic filtering yet

---

### 3. Model Hallucination / Weak Reasoning

Example:

* MNPI expanded incorrectly

### 🔍 Learning

Small models (gemma:2b):

* Cannot reliably infer definitions
* May hallucinate expansions

👉 Prompting helps, but model capacity is the bottleneck

---

## ⚠️ Key System Behavior Observed

| Component  | Status      | Behavior                 |
| ---------- | ----------- | ------------------------ |
| Embeddings | ⚠️ Slow     | Works with timeouts      |
| Retrieval  | ✅ Good      | Multi-collection works   |
| Reranker   | ⚠️ Unstable | Fallback works correctly |
| Generation | ⚠️ Slow     | CPU bottleneck           |

---

## 🧪 Testing Verdict

✅ End-to-end working

Even with:

* Partial ingestion
* Reranker failures
* CPU-only setup

👉 System is **functionally correct**

---

## 🚀 Practical Conclusion

Your system is now:

* Architecturally sound
* Fault-tolerant (important!)
* Ready for cloud upgrade

---

## 🧭 What Matters Next (Not Urgent Now)

* Better model (cloud GPU)
* Better embeddings
* Improve chunking
* Add retry for embeddings
* Add structured evaluation

---

# ⚖️ Reranker On vs Off – Observations

## 🧪 Setup
- Tested with reranker container **ON vs OFF**
- Same queries executed across both setups

---

## 🚀 Observations

### ✅ Without reranker
- Responses returned **faster (<30s on CPU)**
- System remained **stable even when reranker unavailable**
- Retrieval quality **acceptable but less precise**
- More cases of:
  - Irrelevant chunks
  - “Not found” despite partial context

---

### ⚠️ With reranker (cross-encoder on CPU)
- Significant **latency increase**
- Frequent **timeouts / failures**
- Better **chunk relevance when it works**
- Not reliable for local CPU testing

---

## 🧠 Key Learnings

- Cross-encoder rerankers are **computationally expensive**
- CPU-based reranking is **not practical for low-latency systems**
- A **fallback mechanism is essential** (system should not fail if reranker is down)
- Vector search alone is **fast but less precise**
- Reranker improves **precision, not recall**

---

## 🏗️ Industry Insight

Production systems typically:

- Use **GPU-based rerankers** OR
- Use **lighter / distilled rerankers** OR
- Skip reranking and rely on:
  - Better embeddings
  - Hybrid search (BM25 + vector)
  - Query rewriting

---

## 🔧 Current Decision

- Keep reranker as **optional (fallback-safe) component**
- Default mode can run **without reranker for local testing**
- Plan to revisit reranker during **GCP deployment (GPU)**

---

## 🚀 RAG Enhancements: Hybrid Retrieval + Caching Layer (2026-05-04)

### 🧠 What was added

We introduced a lightweight caching layer and reinforced hybrid retrieval in the RAG pipeline to improve latency, reduce redundant computation, and stabilize response quality.

---

## ⚡ 1. Caching Layer (In-Memory TTL Cache)

### 📌 Purpose
Reduce repeated computation for:
- Embeddings (expensive model calls)
- Final LLM responses (repeat queries)

### 📌 Implementation
We implemented a simple in-memory TTL cache:

- `apps/api/app/services/cache.py`
  - `SimpleTTLCache` with expiration support
- `apps/api/app/dependencies/cache.py`
  - Separate cache instances:
    - `embedding_cache` (TTL: 1 hour)
    - `retrieval_cache` (TTL: 5 minutes conceptually used for responses)

### 📌 Usage in RAG pipeline
In `rag_service.py`:
- Response-level caching:
  - `cache.get("response:{query}")`
  - `cache.set("response:{query}", result)`
- Embedding-level caching:
  - `cache.get("embedding:{query}")`
  - avoids recomputing embeddings for repeated queries

### 📌 Benefits
- Eliminates duplicate LLM calls for repeated questions
- Reduces embedding generation cost
- Improves perceived API latency significantly

---

## 🔍 2. Hybrid Retrieval (Dense + Sparse)

### 📌 Architecture
We use a hybrid approach:
- **Dense retrieval** → Qdrant vector search
- **Sparse retrieval** → BM25 (rank_bm25)

### 📌 Flow
1. Query is routed to collections (policy vs SEC docs)
2. Dense vectors retrieved from Qdrant
3. BM25 retrieves keyword-based matches
4. Both results are merged + deduplicated
5. Final chunks passed to reranker

---

## 🧩 3. Observed Behavior

### ✅ Working correctly:
- Cache hits logged:
  - `[CACHE] Response hit`
  - `[CACHE] Embedding stored`
- Hybrid retrieval returning both:
  - Qdrant (semantic)
  - BM25 (lexical)
- Reranker improving final context selection

### ⚠️ Known issue:
- Occasional reranker timeout:

Needs:
- timeout tuning OR
- retry fallback OR
- async batching optimization

---

## 📈 Impact

| Component        | Improvement |
|----------------|-------------|
| Embeddings     | Reduced duplicate calls |
| Response time  | Faster repeated queries |
| Retrieval      | More robust (semantic + keyword) |
| System design  | Cache-ready for future Redis migration |

---

## 🔮 Next Steps

- Replace in-memory cache with Redis (GCP Memorystore compatible)
- Add cache invalidation strategy for document updates
- Improve reranker resilience (timeouts + fallback scoring)
- Add cache metrics (hit/miss logging)

## 🚀 Session Update: Hybrid RAG + Compliance Scan + MCP Integration

### ✅ What Was Implemented

#### 1. Hybrid Retrieval (Dense + BM25)
- Added BM25-based sparse retrieval using `hybrid_retriever`
- Combined with vector search (Qdrant) for improved recall
- Enabled for both:
  - `sec_docs`
  - `policies`
- Observed improved chunk coverage and retrieval diversity

---

#### 2. Multi-Level Caching
- Implemented in-memory TTL cache:
  - Embedding cache
  - Response cache
- Reduced redundant LLM + embedding calls
- Verified via logs (`[CACHE] hit`)

---

#### 3. Compliance Scan Pipeline
- New service: `compliance_service.py`
- Flow:
  - Fetch email (JSON-based mock DB)
  - Retrieve relevant policies via RAG
  - Run LLM-based violation detection
- Output:
  - violations[]
  - risk_level
  - explanation

---

#### 4. MCP Server Integration
- Built MCP tool: `compliance_scan`
- Registered via decorator pattern
- Exposed via `/execute` endpoint
- Enabled agent/tool-based invocation

---

#### 5. LangGraph Agent Integration
- Added MCP tool call node
- Agent can now:
  - Route to compliance scan
  - Execute via MCP
- Clean separation between:
  - Agent logic
  - Tool execution
  - Backend services

---

### 🔍 Key Observations

- Retrieval quality directly impacts compliance detection accuracy
- Policies must include:
  - explicit indicators
  - keywords / patterns
- LLM requires strong prompting for:
  - risk sensitivity
  - partial violation detection
- BM25 significantly improved recall vs vector-only search

---

### ⚠️ Issues Faced

- Missing BM25 for policies → fixed
- MCP tool not found → missing import in `main.py`
- Reranker startup delay → requires warm-up / retry handling
- Weak policy definitions → caused false negatives

---

### 🔐 Security / Repo Hygiene

- Removed sensitive files from version control:
  - `emails.json`
  - `policies.txt`
- Updated `.gitignore` accordingly

---

### 🧭 Next Steps

- Improve policy structure with:
  - violation indicators
  - heuristic rules
- Move email storage to Postgres
- Store scan results (violations) in DB
- Add batch scan API
- Build compliance dashboard (risk view)
- Add retry + fallback for reranker
- Introduce evaluation (RAGAS / custom metrics)

---

### 💡 Key Learning

This system evolved from:
- basic RAG QA → to
- hybrid retrieval → to
- agent + MCP tool system → to
- **policy-driven compliance detection engine**

This significantly improves real-world applicability and system design depth.

## 📌 Session Update: Compliance Scan Pipeline

### ✅ What was built

- Implemented **email compliance scanning pipeline**
  - Emails stored in Postgres
  - Policies stored in Qdrant
  - RAG used for policy-aware reasoning

- Added new API:
  - `POST /scan-email?email_id=...`

- Integrated **hybrid retrieval**
  - Vector search (Qdrant)
  - BM25 keyword search
  - Merged + reranked results

- Added **MCP tool**
  - Tool: `compliance_scan`
  - Enables agent/tool-based execution via MCP server

- Wired into **LangGraph agent**
  - Enables orchestration across tools (RAG + compliance)

---

### 🧠 Key Learnings

- RAG should act as a **reasoning layer**, not just retrieval
- Prompt quality directly impacts risk detection accuracy
- BM25 significantly improves recall for keyword-heavy policies
- Reranker improves precision after hybrid retrieval
- Caching can hide prompt improvements → must invalidate during testing
- MCP tools require decorator-based registration (not function calls)

---

### ⚠️ Issues Faced

- Reranker startup delay caused initial connection failures
- Incorrect tool registration (`register_tool` usage mismatch)
- Import path issues inside Docker (`app` module not found)
- Prompt bug (`context` undefined) caused runtime failure
- Cache returning stale responses during prompt iteration

---

### 🚀 Next Steps

- Add **batch email scanning** (multiple emails → risk report)
- Introduce **confidence scores** in output
- Normalize structured JSON output (avoid truncation issues)
- Expand policy definitions with:
  - keyword patterns
  - proximity rules
  - heuristic signals
- Build **dashboard-style output** (risk summary, counts by category)

---