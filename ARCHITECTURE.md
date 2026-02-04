## Entitlements Chat Assistant — Detailed Architecture & Flow

### Goals

- Answer questions about the **Entitlements Platform** using:
  - **Knowledge base** (code, docs, DB schema, relationships)
  - **Live DB data** (for questions like “list users in dept who can access app”)
- Provide **traceability** (citations) and **guardrails** (safe SQL, read-only).

---

## Components

### 1) Knowledge Sources

- **DB schema + relations**: `entitlements-app/db/schema.sql`
- **Operational docs**: `entitlements-app/README.md`, `QUERYING_RELATIONSHIPS.md`, `API_AND_UI_GUIDE.md`
- **Backend service code**: `entitlements-app/backend/**`
- **Frontend UI code** (optional for help/explanations): `entitlements-app/frontend/**`

### 2) Ingestion & Indexing (Offline / On-demand)

**Purpose**: Convert source artifacts into searchable chunks for retrieval.

Pipeline:
- **Collect**: traverse configured directories/files
- **Normalize**: strip noise (build artifacts, node_modules, target/, etc.)
- **Chunk**: split into ~500–1200 token chunks with overlaps
- **Embed**: create dense vectors using a configured embeddings model
- **Store**: persist chunks + metadata + vectors in Postgres (`pgvector`)

Stored metadata per chunk:
- source path
- content type (ddl/java/md/tsx/etc.)
- chunk id, offsets
- optional tags (e.g. “schema”, “api”, “relationships”)

### 3) Retrieval (Online, per question)

For each user message:
- Embed the question
- Perform vector similarity search over stored chunks
- Select top-K chunks (plus optional filters: “schema-only” etc.)
- Provide those chunks as **context** to the LLM

### 4) Answering Modes

We support two modes (auto-selected by a router):

#### A) Knowledge-only (RAG)

Used when:
- user asks about “how it works”, “what table”, “what does X mean”
- no need for live DB queries

Flow:
- retrieve chunks → prompt LLM → answer with citations (file paths)

#### B) Data Q&A (RAG + Safe SQL tool)

Used when:
- question asks for “list”, “count”, “which users/departments”
- needs live data from Postgres

Flow:
- retrieve chunks (schema + relationship docs) to understand joins
- route to **SQL tool**:
  - choose from allowlisted query templates
  - fill parameters (app code, department code, region code)
  - execute read-only SQL
  - return rows (limited)
- LLM summarizes results and provides the SQL used (optional)

### 5) Guardrails & Safety

- DB access is **read-only**
- SQL is **template-based** / allowlisted (v1), not arbitrary
- result limits enforced (e.g., 100 rows)
- no secrets included in answers

### 6) Deployment Topology

- `entitlements-service` (Spring Boot): `http://localhost:8080`
- `chat-rag-service` (FastAPI): `http://localhost:8000`
- `entitlements-ui` (Vite React): `http://localhost:3000`

The UI calls the chat service; the chat service reads Postgres.

---

## Runtime Request/Response Flow (UI → Chat → DB/Vector)

1. User types question in bottom chat widget (React).
2. UI POSTs `{conversationId, message}` to chat backend.
3. Chat backend:
   - classifies mode: knowledge vs data
   - retrieves relevant chunks from pgvector
   - if data-mode: executes safe SQL templates
   - calls LLM with context + (optional) SQL results
4. Returns:
   - assistant message
   - citations (source paths / chunk ids)
   - (optional) SQL executed + row counts
5. UI renders assistant reply and citation links.


