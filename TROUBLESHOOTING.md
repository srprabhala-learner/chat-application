# Troubleshooting Guide for Option 1

## Issue: Simple Queries Not Working

### Problem
Queries like "what is the name of user whose username is user00001" are not being handled correctly.

### Fixes Applied

1. **Improved Intent Classification**
   - Added examples for simple user queries
   - Clarified that data queries should be `generic_sql`, not `knowledge_only`
   - Added explicit instruction: "Questions asking for specific data values should be classified as 'generic_sql'"

2. **Enhanced SQL Generation**
   - Added fallback to full schema prompt if retrieval fails
   - Improved prompt with examples for simple queries
   - Better JSON parsing (handles markdown code blocks)
   - Smarter LIMIT handling (LIMIT 1 for single-value queries)
   - More explicit instructions about table/column names

3. **Better Logging**
   - Added detailed logging throughout the pipeline
   - Logs show: intent classification, schema retrieval, SQL generation, execution
   - Easier to debug where failures occur

4. **Schema Retrieval Improvements**
   - Better logging of retrieval process
   - Fallback mechanism if no schema chunks found

## How to Debug

### 1. Check Logs

The system now logs extensively. Look for:

```
Option 1: Processing question: ...
Option 1: Classified intent: ...
Schema retrieval: Searching for schema context...
Enhanced SQL: Starting generation...
Enhanced SQL: Generated SQL: ...
```

### 2. Test Intent Classification

```bash
# Should classify as "generic_sql", not "knowledge_only"
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is the name of user whose username is user00001"}'
```

Check logs for:
```
Option 1: Classified intent: {'intent': 'generic_sql', ...}
```

If it shows `knowledge_only`, the intent classifier needs more examples.

### 3. Check Schema Retrieval

Look for logs like:
```
Schema retrieval: Found X schema-specific hits
Schema retrieval: Using Y relevant hits
```

If it shows "No schema chunks found", the schema might not be ingested properly.

### 4. Check SQL Generation

Look for:
```
Enhanced SQL: Generated SQL: SELECT ...
```

If SQL generation fails, check:
- Is the schema context being retrieved?
- Is the OpenAI API key set?
- Are there errors in the JSON parsing?

### 5. Verify Schema Ingestion

Make sure schema was parsed during ingestion:

```bash
curl -X POST http://localhost:8000/api/ingest
```

Check response for:
```json
{
  "schema_parsed": true,
  ...
}
```

## Common Issues

### Issue 1: Query Classified as "knowledge_only"

**Symptom**: Simple data queries are being answered with documentation instead of SQL.

**Fix**: The intent classifier has been updated with better examples. If still happening:
1. Check logs for intent classification
2. Add more examples to `intent_router.py` if needed
3. Ensure the question clearly asks for data (not "how does it work")

### Issue 2: Schema Not Found

**Symptom**: "No schema chunks found" in logs.

**Fix**:
1. Re-run ingestion: `curl -X POST http://localhost:8000/api/ingest`
2. Verify `entitlements-app/db/schema.sql` exists
3. Check that schema parsing succeeded (look for "Schema graph built" in logs)

### Issue 3: SQL Generation Fails

**Symptom**: SQL generation returns None.

**Fix**:
1. Check OpenAI API key is set
2. Check logs for JSON parsing errors
3. Verify schema context is being retrieved
4. Check if fallback schema is being used

### Issue 4: Wrong SQL Generated

**Symptom**: SQL is generated but doesn't match the question.

**Fix**:
1. Check the schema context being used (in logs)
2. Verify table/column names match the schema
3. Check if few-shot examples are helping or hurting
4. Review the query bank for similar successful queries

## Testing Simple Queries

Test these queries to verify the system works:

```bash
# Simple user query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is the name of user whose username is user00001"}'

# Should generate: SELECT first_name, last_name FROM identity.user_account WHERE username = 'user00001' LIMIT 1;

# User email query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show me the email of user user00001"}'

# List query
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "list all users in department DEPT_1"}'
```

## Expected Behavior

For "what is the name of user whose username is user00001":

1. **Intent Classification**: Should be `generic_sql`
2. **Schema Retrieval**: Should find `identity.user_account` table schema
3. **SQL Generation**: Should generate:
   ```sql
   SELECT first_name, last_name FROM identity.user_account WHERE username = 'user00001' LIMIT 1;
   ```
4. **Execution**: Should return the user's name
5. **Response**: Should provide natural language answer with the name

## Next Steps if Still Not Working

1. **Check Query Bank**: Look at `backend/app/query_bank.json` to see if similar queries succeeded
2. **Add Examples**: If a pattern keeps failing, add it to the query bank manually
3. **Review Logs**: Full logs will show exactly where the pipeline is failing
4. **Test with Legacy Mode**: Switch to `MODE_OF_IMPLEMENTATION=legacy` to compare behavior

## Logging Levels

To see more detailed logs, you can adjust logging level in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)  # More verbose
```

