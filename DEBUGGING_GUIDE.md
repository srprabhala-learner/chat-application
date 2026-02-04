# Debugging Guide for Policy Rule Queries

## Problem

Query "what is the policy rule for application with app code APP_1" is not working.

## Debugging Steps

### 1. Check Schema Retrieval

Test if the schema is being retrieved correctly:

```bash
curl -X POST http://localhost:8000/api/debug/schema-retrieval \
  -H "Content-Type: application/json" \
  -d '{"question": "what is the policy rule for application with app code APP_1"}'
```

**Expected**: Should return schema context containing `entitlement.policy_rule` table information.

**If empty or missing policy_rule**: The schema might not be ingested properly. Re-run ingestion.

### 2. Check SQL Generation

Test SQL generation directly:

```bash
curl -X POST http://localhost:8000/api/debug/sql-generation \
  -H "Content-Type: application/json" \
  -d '{"question": "what is the policy rule for application with app code APP_1"}'
```

**Expected**: Should return a `sql_result` with generated SQL.

**If None**: Check the logs for:
- What SQL was attempted to be generated
- What error occurred
- What schema context was provided

### 3. Check Logs

Look for these log messages in the server output:

```
Option 1: Processing question: what is the policy rule for application with app code APP_1
Option 1: Classified intent: {'intent': 'generic_sql', ...}
Schema retrieval: Searching for schema context...
Schema retrieval: Found X schema-specific hits
Enhanced SQL: Retrieved schema context length: X chars
Enhanced SQL: Generated SQL: SELECT ...
```

**Common Issues**:

1. **Intent classified as "knowledge_only"**
   - Fix: Add more examples to intent router

2. **Schema context too short or missing policy_rule**
   - Fix: Re-run ingestion to ensure schema is parsed and stored

3. **SQL generation returns None**
   - Check: What did the LLM return? (see logs)
   - Check: Was JSON parsing successful?
   - Check: Did SQL pass safety checks?

4. **SQL validation fails**
   - Check: What was the validation error?
   - Check: Is the SQL syntax correct?

5. **SQL execution fails**
   - Check: What was the database error?
   - Check: Does the table exist?
   - Check: Are column names correct?

### 4. Verify Schema Ingestion

Check if policy_rule table was ingested:

```bash
# Connect to database
psql -U entitlements_user -d entitlements_platform

# Check if schema chunks exist
SELECT chunk_id, source_path 
FROM rag.documents 
WHERE chunk_id LIKE 'schema:%policy%' 
LIMIT 10;
```

### 5. Test Direct SQL

Test the SQL directly in the database:

```sql
SELECT 
  pr.id,
  pr.policy_set_id,
  pr.application_id,
  a.code AS app_code,
  a.name AS app_name,
  pr.grant_type,
  pr.priority,
  pr.condition_logic,
  pr.created_at
FROM entitlement.policy_rule pr
JOIN catalog.application a ON a.id = pr.application_id
WHERE a.code = 'APP_1'
ORDER BY pr.priority, pr.id
LIMIT 200;
```

**If this works**: The issue is in SQL generation, not the database.

**If this fails**: Check database schema and data.

### 6. Check Query Bank

Look at `backend/app/query_bank.json` to see if there are similar failed queries:

```bash
cat backend/app/query_bank.json | grep -A 5 -B 5 "policy"
```

### 7. Manual Test with Enhanced SQL Generator

You can test the SQL generator directly in Python:

```python
from app.sql_generate_v2 import EnhancedSQLGenerator

generator = EnhancedSQLGenerator()
result = generator.generate_and_execute("what is the policy rule for application with app code APP_1")
print(result)
```

## Common Fixes

### Fix 1: Re-run Ingestion

```bash
curl -X POST http://localhost:8000/api/ingest
```

This ensures:
- Schema is parsed from DDL
- Schema chunks are stored in vector DB
- Policy_rule table is available for retrieval

### Fix 2: Check Mode

Ensure you're using Option 1:

```bash
# Check .env file
cat backend/.env | grep MODE_OF_IMPLEMENTATION
# Should be: MODE_OF_IMPLEMENTATION=option1
```

### Fix 3: Check OpenAI API Key

```bash
# Check .env file
cat backend/.env | grep OPENAI_API_KEY
# Should have a valid key
```

### Fix 4: Increase Schema Context

If schema retrieval is failing, the fallback should kick in (uses full schema prompt). Check logs to see if fallback is being used.

### Fix 5: Check Database Connection

```bash
# Test database connection
psql -U entitlements_user -d entitlements_platform -c "SELECT COUNT(*) FROM entitlement.policy_rule;"
```

## Expected SQL

For "what is the policy rule for application with app code APP_1", the system should generate:

```sql
SELECT 
  pr.id,
  pr.policy_set_id,
  pr.application_id,
  a.code AS app_code,
  a.name AS app_name,
  pr.grant_type,
  pr.priority,
  pr.condition_logic,
  pr.created_at
FROM entitlement.policy_rule pr
JOIN catalog.application a ON a.id = pr.application_id
WHERE a.code = 'APP_1'
ORDER BY pr.priority, pr.id
LIMIT 200;
```

## Debug Endpoints

Two new debug endpoints are available:

1. **`/api/debug/schema-retrieval`**: Test schema retrieval
2. **`/api/debug/sql-generation`**: Test SQL generation

Use these to isolate where the problem occurs.

## Next Steps

1. Run the debug endpoints to see what's happening
2. Check server logs for detailed error messages
3. Verify schema ingestion completed successfully
4. Test the SQL directly in the database
5. Check if the issue is with:
   - Schema retrieval (no policy_rule found)
   - SQL generation (LLM not generating correct SQL)
   - SQL validation (syntax error)
   - SQL execution (database error)

