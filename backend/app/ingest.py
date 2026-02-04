from pathlib import Path
import logging

from app.chunking import chunk_text
from app.embeddings import embed_texts, get_model
from app.ingest_sources import iter_source_docs
from app.rag_store import ensure_rag_schema_and_table, upsert_chunks
from app.schema_graph import SchemaGraphBuilder

logger = logging.getLogger("entitlements-chat.ingest")


def run_ingestion(entitlements_root: Path) -> dict:
    """
    Run ingestion pipeline:
    1. Ingest source documents (code, docs, etc.)
    2. Parse and store schema knowledge graph (for Option 1+)
    """
    model = get_model()
    vector_dim = model.get_sentence_embedding_dimension()
    ensure_rag_schema_and_table(vector_dim=vector_dim)

    # 1. Ingest regular source documents
    docs = iter_source_docs(entitlements_root)
    chunks_all = []
    for d in docs:
        chunks = chunk_text(d.source_path, d.text)
        chunks_all.extend(chunks)

    # 2. Parse and store schema knowledge graph (for Option 1)
    schema_chunks = []
    schema_ddl_path = entitlements_root / "db" / "schema.sql"
    if schema_ddl_path.exists():
        logger.info("Parsing schema DDL for knowledge graph...")
        try:
            schema_builder = SchemaGraphBuilder()
            schema_result = schema_builder.build_and_store(
                schema_ddl_path, entitlements_root
            )
            logger.info(
                f"Schema graph built: {schema_result['tables']} tables, "
                f"{schema_result['relationships']} relationships, "
                f"{schema_result['chunks']} chunks"
            )
        except Exception as e:
            logger.warning(f"Failed to parse schema DDL: {e}")
            # Continue with regular ingestion even if schema parsing fails

    # Batch embeddings for regular chunks
    contents = [c.content for c in chunks_all]
    vectors = []
    batch_size = 64
    for i in range(0, len(contents), batch_size):
        vectors.extend(embed_texts(contents[i : i + batch_size]))

    rows = []
    for c, v in zip(chunks_all, vectors):
        rows.append(
            {
                "chunk_id": c.chunk_id,
                "source_path": c.source_path,
                "content": c.content,
                "embedding": v,
            }
        )

    upserted = upsert_chunks(rows)
    return {
        "sources": len(docs),
        "chunks": len(chunks_all),
        "upserted": upserted,
        "schema_parsed": schema_ddl_path.exists() if schema_ddl_path else False,
    }


