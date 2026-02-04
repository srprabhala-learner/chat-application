# Option 1 Implementation: Enhanced RAG + Structured Schema Understanding

## Overview

Option 1 implements a production-grade AI-driven chat application that:
- **Automatically learns** database schema relationships from DDL files
- **Retrieves relevant schema** context using RAG (not the entire schema)
- **Generates SQL** with self-validation and correction
- **Learns from successful queries** via a query bank
- **Handles arbitrary questions** without requiring templates

## Architecture

```
User Question
    ↓
Intent Classification (Knowledge vs Data)
    ↓
┌─────────────────┬──────────────────┐
│ Knowledge Only  │ Data Query       │
│ → RAG Only      │ → Enhanced SQL   │
└─────────────────┴──────────────────┘
                        ↓
            Schema Retrieval (RAG)
            - Only relevant tables/columns
            - Relationships discovered
                        ↓
            SQL Generation
            - Few-shot examples from query bank
            - Self-validation
            - Self-correction on errors
                        ↓
            Execute & Store Pattern
```

## Key Components

### 1. Schema Parser (`app/schema_parser.py`)
- Parses PostgreSQL DDL files
- Extracts tables, columns, data types, constraints
- Discovers foreign key relationships
- Builds structured knowledge graph

### 2. Schema Knowledge Graph (`app/schema_graph.py`)
- Stores schema as structured chunks in vector DB
- Table-level chunks with columns and relationships
- Relationship chunks showing foreign keys
- JSON representation for programmatic access

### 3. Enhanced Schema Retrieval (`app/schema_retrieval.py`)
- Uses RAG to find relevant schema chunks
- Only retrieves tables/columns mentioned in question
- Provides context-aware schema snippets

### 4. Enhanced Text-to-SQL (`app/sql_generate_v2.py`)
- Uses retrieved schema context (not full schema)
- Few-shot learning from query bank
- Self-validation: checks SQL syntax
- Self-correction: fixes errors automatically
- Stores successful patterns

### 5. Query Bank (`app/query_bank.py`)
- Stores successful query examples
- Provides few-shot examples for similar questions
- Tracks success/failure rates
- Enables continuous learning

### 6. Option 1 Handler (`app/chat_handlers.py`)
- Orchestrates the entire flow
- Routes knowledge vs data questions
- Handles errors gracefully

## Setup

### 1. Configure Mode

Add to `backend/.env`:
```bash
MODE_OF_IMPLEMENTATION=option1
```

Available modes:
- `option1`: Enhanced RAG + Structured Schema (this implementation)
- `option2`: Agentic Architecture (to be implemented)
- `option3`: Fine-Tuned Model (to be implemented)
- `option4`: Hybrid (to be implemented)
- `legacy`: Template-based approach (default)

### 2. Run Ingestion

The ingestion process will automatically:
1. Parse `entitlements-app/db/schema.sql`
2. Build schema knowledge graph
3. Store schema chunks in vector DB

```bash
cd backend
python3 -m uvicorn app.main:app --reload
# In another terminal:
curl -X POST http://localhost:8000/api/ingest
```

### 3. Test

```bash
# Test with a data question
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me all users in Department 5 who have access to APP_3"}'

# Test with a knowledge question
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How does the entitlements platform work?"}'
```

## How It Works

### Example: "Show users from DEPT_5 who have access to APP_3"

1. **Intent Classification**
   - Classifies as data query (not knowledge-only)

2. **Schema Retrieval**
   - RAG finds relevant chunks:
     - `identity.user_account` table
     - `core.organization_unit` table
     - `catalog.application` table
     - `catalog.application_availability` table
     - Relationships between these tables

3. **SQL Generation**
   - Uses retrieved schema context
   - Gets few-shot examples from query bank (if available)
   - Generates SQL with proper JOINs

4. **Validation & Execution**
   - Validates SQL syntax
   - Executes query
   - If error: self-corrects and retries

5. **Learning**
   - Stores successful pattern in query bank
   - Future similar questions will use this as example

## Advantages Over Legacy Approach

| Feature | Legacy | Option 1 |
|--------|--------|----------|
| **Schema Understanding** | Static markdown | Dynamic, learned from DDL |
| **Query Generation** | Templates only | Generic, handles any question |
| **Schema Context** | Full schema | Only relevant parts |
| **Error Handling** | Manual | Self-correction |
| **Learning** | None | Query bank |
| **Maintenance** | Add templates | Automatic |

## Query Bank

The query bank (`backend/app/query_bank.json`) stores:
- Successful query patterns
- Failed queries (for learning)
- Execution metrics
- Table usage patterns

This enables:
- Few-shot learning for similar questions
- Pattern recognition
- Continuous improvement

## Monitoring

Check query bank statistics:
```python
from app.query_bank import QueryBank
bank = QueryBank()
stats = bank.get_statistics()
print(stats)
```

## Troubleshooting

### Schema Not Parsing
- Check that `entitlements-app/db/schema.sql` exists
- Verify DDL syntax is valid PostgreSQL
- Check logs for parsing errors

### SQL Generation Failing
- Check query bank for similar successful queries
- Verify schema chunks are in vector DB
- Check OpenAI API key and model settings

### Self-Correction Not Working
- Ensure OpenAI API key is set
- Check model has sufficient context window
- Review error messages in logs

## Next Steps

To implement Option 2, 3, or 4:
1. Create new handler class in `chat_handlers.py`
2. Implement `handle()` method
3. Update `get_handler()` to return new handler
4. Set `MODE_OF_IMPLEMENTATION` in `.env`

## Files Created/Modified

**New Files:**
- `app/schema_parser.py` - DDL parser
- `app/schema_graph.py` - Knowledge graph builder
- `app/schema_retrieval.py` - RAG-based schema retrieval
- `app/sql_generate_v2.py` - Enhanced SQL generator
- `app/query_bank.py` - Query pattern storage
- `app/chat_handlers.py` - Modular handler system

**Modified Files:**
- `app/config.py` - Added `MODE_OF_IMPLEMENTATION`
- `app/main.py` - Handler-based routing
- `app/ingest.py` - Schema parsing integration

