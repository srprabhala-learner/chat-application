## Chat App Entitlements — Setup

### 1) Ensure Postgres has pgvector

Connect to your database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2) Create `.env` (IMPORTANT)

Make sure the file name is exactly **`.env`** (not `.evn`) and it is located at:

- `/home/srprabhala/Documents/Learning/chat-app-entitlements/backend/.env`

Add at least:

- `OPENAI_API_KEY=...`
- `MODE_OF_IMPLEMENTATION=option1` (or `legacy`, `option2`, `option3`, `option4`)

**Implementation Modes:**
- `option1`: Enhanced RAG + Structured Schema Understanding (recommended, see `OPTION1_IMPLEMENTATION.md`)
- `option2`: Agentic Architecture (to be implemented)
- `option3`: Fine-Tuned Model (to be implemented)
- `option4`: Hybrid (to be implemented)
- `legacy`: Template-based approach (default, original implementation)

### 3) Install and run chat backend

```bash
cd /home/srprabhala/Documents/Learning/chat-app-entitlements/backend
python -m venv .venv
source .venv/bin/activate
 pip install -r requirements.txt
 # Put your key in backend/.env (recommended) OR export it
./run.sh
```

Health check:

```bash
curl http://localhost:8000/health
```

### 4) Ingest the entitlements knowledge base

This will read files from the sibling folder `entitlements-app/` and store embeddings in Postgres.

```bash
curl -X POST http://localhost:8000/api/ingest
```

### 5) Run the Entitlements UI with the embedded chat widget

```bash
cd /home/srprabhala/Documents/Learning/entitlements-app/frontend
npm install
npm run dev
```

Open `http://localhost:3000` and use the **Chat** button (bottom-right).

---

## Notes

- The UI proxies `/chatapi/*` to `http://localhost:8000/*` (see `entitlements-app/frontend/vite.config.js`).
- Current chat behavior (v0.2): retrieval-only (shows top relevant source files). Next step is to add:
  - LLM response generation
  - Safe SQL answering for live data questions


