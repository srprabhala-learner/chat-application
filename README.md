## Chat App for Entitlements Platform (RAG)

This project adds a **chat assistant** for the Entitlements Platform.

### What it can answer

- **Knowledge questions (RAG over code + DB schema)**  
  Example: “Explain how the entitlements platform determines app access.”

- **Data questions (RAG + safe SQL tool)**  
  Example: “Which departments have access to Application 1?”  
  Example: “List users from Department 1 who have access to APP_1.”

### High-level architecture (detailed doc below)

- **Knowledge ingestion**: reads the Entitlements Platform repository artifacts (DDL, seed data notes, markdown docs, Spring Boot code) and stores embeddings in PostgreSQL + `pgvector`.
- **Retrieval**: for each user question, retrieves the most relevant chunks and provides them to the LLM with citations.
- **Optional SQL tool** (read-only): for questions that require live data, generates/uses parameterized SQL templates (guarded), executes them against Postgres, and summarizes results.

### Projects involved

- **Backend**: this repo (`chat-app-entitlements`) runs the RAG service.
- **Frontend**: the existing React UI in `entitlements-app/frontend` will get a small chat widget pinned to the bottom-right.


