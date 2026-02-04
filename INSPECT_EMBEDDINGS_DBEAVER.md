# How to Inspect Vector Embeddings in PostgreSQL using DBeaver

## Table Structure

The vector embeddings are stored in:
- **Schema**: `rag` (default, configurable via `RAG_SCHEMA` env var)
- **Table**: `documents` (default, configurable via `RAG_TABLE` env var)
- **Database**: `entitlements_platform` (default)

### Table Schema

```sql
CREATE TABLE rag.documents (
  id BIGSERIAL PRIMARY KEY,
  chunk_id TEXT NOT NULL UNIQUE,
  source_path TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding vector(384) NOT NULL,  -- 384 dimensions (all-MiniLM-L6-v2)
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Note**: The embedding dimension is **384** (from `sentence-transformers/all-MiniLM-L6-v2` model).

---

## SQL Queries for DBeaver

### 1. View All Documents (Basic Info)

```sql
SELECT 
    id,
    chunk_id,
    source_path,
    LENGTH(content) AS content_length,
    created_at
FROM rag.documents
ORDER BY created_at DESC
LIMIT 50;
```

### 2. View Document Content (First 100 Characters)

```sql
SELECT 
    chunk_id,
    source_path,
    LEFT(content, 100) || '...' AS content_preview,
    created_at
FROM rag.documents
ORDER BY source_path, chunk_id
LIMIT 100;
```

### 3. Count Documents by Source

```sql
SELECT 
    source_path,
    COUNT(*) AS chunk_count,
    MIN(created_at) AS first_ingested,
    MAX(created_at) AS last_ingested
FROM rag.documents
GROUP BY source_path
ORDER BY chunk_count DESC;
```

### 4. View Full Content of a Specific Document

```sql
SELECT 
    chunk_id,
    source_path,
    content,
    created_at
FROM rag.documents
WHERE chunk_id = 'your-chunk-id-here'
   OR source_path LIKE '%schema.sql%'
LIMIT 10;
```

### 5. View Embedding Vector (as Text)

**Note**: DBeaver may not display the `vector` type directly. You can cast it to text:

```sql
SELECT 
    chunk_id,
    source_path,
    embedding::text AS embedding_text,
    LENGTH(embedding::text) AS embedding_length
FROM rag.documents
LIMIT 5;
```

### 6. View Embedding Dimensions

```sql
SELECT 
    chunk_id,
    array_length(string_to_array(trim(embedding::text, '[]'), ','), 1) AS dimensions
FROM rag.documents
LIMIT 5;
```

### 7. Find Similar Documents (Vector Similarity Search)

To find documents similar to a query, you need to:
1. Generate an embedding for your query text
2. Use pgvector's cosine distance operator (`<=>`)

**Example**: Find documents similar to "user entitlements"

```sql
-- First, you'd need to generate the embedding for "user entitlements"
-- This is typically done in Python, but for demonstration:
-- Let's find documents that mention "user" in their content

SELECT 
    chunk_id,
    source_path,
    LEFT(content, 200) AS content_preview,
    created_at
FROM rag.documents
WHERE content ILIKE '%user%entitlement%'
ORDER BY created_at DESC
LIMIT 10;
```

### 8. Check Index Status

```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'rag'
  AND tablename = 'documents';
```

### 9. View Statistics

```sql
SELECT 
    COUNT(*) AS total_chunks,
    COUNT(DISTINCT source_path) AS unique_sources,
    MIN(created_at) AS oldest_chunk,
    MAX(created_at) AS newest_chunk,
    AVG(LENGTH(content)) AS avg_content_length
FROM rag.documents;
```

### 10. Find Schema-Related Chunks

```sql
SELECT 
    chunk_id,
    source_path,
    LEFT(content, 150) AS content_preview
FROM rag.documents
WHERE chunk_id LIKE 'schema:%'
   OR source_path LIKE '%schema.sql%'
ORDER BY chunk_id
LIMIT 20;
```

### 11. Find Architecture-Related Chunks

```sql
SELECT 
    chunk_id,
    source_path,
    LEFT(content, 200) AS content_preview
FROM rag.documents
WHERE chunk_id LIKE '%architecture%'
   OR source_path LIKE '%BUSINESS_ARCHITECTURE%'
   OR content ILIKE '%architecture%'
ORDER BY source_path, chunk_id
LIMIT 20;
```

---

## Understanding the Vector Type in DBeaver

### Displaying Vectors

DBeaver may show the `vector` type in different ways:
- **As text**: `[0.123, -0.456, 0.789, ...]` (384 numbers)
- **As binary**: Raw binary representation
- **As NULL**: If the extension isn't properly loaded

### If Vectors Don't Display

If you see `NULL` or errors when querying the `embedding` column:

1. **Verify pgvector extension is installed**:
   ```sql
   SELECT name, default_version, installed_version 
   FROM pg_available_extensions 
   WHERE name = 'vector';
   ```

2. **Check if extension is enabled in your database**:
   ```sql
   SELECT extname, extversion 
   FROM pg_extension 
   WHERE extname = 'vector';
   ```

3. **If not enabled, enable it** (requires superuser or appropriate privileges):
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

---

## Useful pgvector Functions

### Vector Operations

```sql
-- Cosine distance (lower = more similar)
SELECT 
    chunk_id,
    embedding <=> '[0.1,0.2,0.3,...]'::vector AS cosine_distance
FROM rag.documents
ORDER BY cosine_distance
LIMIT 10;

-- L2 distance (Euclidean)
SELECT 
    chunk_id,
    embedding <-> '[0.1,0.2,0.3,...]'::vector AS l2_distance
FROM rag.documents
ORDER BY l2_distance
LIMIT 10;

-- Inner product (higher = more similar)
SELECT 
    chunk_id,
    embedding <#> '[0.1,0.2,0.3,...]'::vector AS inner_product
FROM rag.documents
ORDER BY inner_product DESC
LIMIT 10;
```

### Vector Dimensions

```sql
-- Get vector dimensions
SELECT 
    chunk_id,
    array_length(embedding::text::float[], 1) AS dimensions
FROM rag.documents
LIMIT 1;
```

---

## Troubleshooting

### Issue: "operator does not exist: vector"

**Solution**: pgvector extension is not installed or enabled.

```sql
-- Check if extension exists
SELECT * FROM pg_available_extensions WHERE name = 'vector';

-- Enable extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: "vector type not found"

**Solution**: The extension is not enabled in your current database.

```sql
-- Enable in the current database
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: DBeaver shows "unknown type" for vector column

**Solution**: This is a DBeaver display issue. The data is still there. You can:
- Cast to text: `embedding::text`
- Use the queries above that cast to text
- The vector operations will still work in SQL

---

## Quick Reference

| Query Purpose | SQL Pattern |
|-------------|-------------|
| List all chunks | `SELECT * FROM rag.documents LIMIT 10;` |
| Count by source | `SELECT source_path, COUNT(*) FROM rag.documents GROUP BY source_path;` |
| View content | `SELECT chunk_id, LEFT(content, 100) FROM rag.documents;` |
| View embedding as text | `SELECT chunk_id, embedding::text FROM rag.documents;` |
| Find similar (needs embedding) | `SELECT * FROM rag.documents ORDER BY embedding <=> $1::vector LIMIT 10;` |

---

## Example: Complete Document Inspection

```sql
-- Get a comprehensive view of a document
SELECT 
    id,
    chunk_id,
    source_path,
    LENGTH(content) AS content_length,
    LEFT(content, 200) AS content_preview,
    array_length(string_to_array(trim(embedding::text, '[]'), ','), 1) AS embedding_dimensions,
    created_at
FROM rag.documents
WHERE source_path LIKE '%schema.sql%'
ORDER BY chunk_id
LIMIT 10;
```

This will show you:
- Document ID and chunk ID
- Source file path
- Content length and preview
- Embedding dimensions (should be 384)
- Creation timestamp

