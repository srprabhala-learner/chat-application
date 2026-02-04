from __future__ import annotations

from app.config import settings
from app.db import get_conn


def _to_vector_literal(vec: list[float]) -> str:
    """
    pgvector accepts text input like: '[0.1,0.2,0.3]'
    We pass embeddings as TEXT and cast to vector in SQL to avoid psycopg treating
    Python lists as double precision[].
    """
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def ensure_rag_schema_and_table(vector_dim: int) -> None:
    """
    Requires pgvector extension installed:
      CREATE EXTENSION IF NOT EXISTS vector;
    """
    schema = settings.rag_schema
    table = settings.rag_table

    ddl = f"""
    CREATE SCHEMA IF NOT EXISTS {schema};

    CREATE TABLE IF NOT EXISTS {schema}.{table} (
      id BIGSERIAL PRIMARY KEY,
      chunk_id TEXT NOT NULL UNIQUE,
      source_path TEXT NOT NULL,
      content TEXT NOT NULL,
      embedding vector({vector_dim}) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_{table}_embedding
      ON {schema}.{table}
      USING ivfflat (embedding vector_cosine_ops);

    CREATE INDEX IF NOT EXISTS idx_{table}_source_path
      ON {schema}.{table} (source_path);
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def upsert_chunks(chunks: list[dict]) -> int:
    """
    chunks: [{chunk_id, source_path, content, embedding}]
    """
    schema = settings.rag_schema
    table = settings.rag_table
    sql = f"""
    INSERT INTO {schema}.{table} (chunk_id, source_path, content, embedding)
    VALUES (%(chunk_id)s, %(source_path)s, %(content)s, %(embedding)s::vector)
    ON CONFLICT (chunk_id) DO UPDATE SET
      source_path = EXCLUDED.source_path,
      content = EXCLUDED.content,
      embedding = EXCLUDED.embedding;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            rows = []
            for c in chunks:
                rows.append(
                    {
                        "chunk_id": c["chunk_id"],
                        "source_path": c["source_path"],
                        "content": c["content"],
                        "embedding": _to_vector_literal(c["embedding"]),
                    }
                )
            cur.executemany(sql, rows)
        conn.commit()
    return len(chunks)


def search(query_embedding: list[float], top_k: int = 8) -> list[dict]:
    schema = settings.rag_schema
    table = settings.rag_table
    sql = f"""
    SELECT chunk_id, source_path, content,
           1 - (embedding <=> %(q)s::vector) AS score
      FROM {schema}.{table}
  ORDER BY embedding <=> %(q)s::vector
     LIMIT %(k)s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"q": _to_vector_literal(query_embedding), "k": top_k})
            return cur.fetchall()


