# Fix: JSON Parsing Error for Markdown-Wrapped Responses

## Problem Identified

From the debug logs, the issue is clear:

```
INFO:entitlements-chat.sql_generate:generate_sql_plan raw LLM content: ```json
{
  "mode": "sql",
  "sql": "SELECT ...",
  "reasoning": "..."
}
```
WARNING:entitlements-chat.sql_generate:generate_sql_plan: JSON decode error
```

**Root Cause:**
- The LLM is generating **correct SQL** wrapped in markdown code blocks (```json ... ```)
- The JSON parser in `sql_generate.py` (legacy) tries to parse the entire string including markdown
- This causes a JSON decode error
- The SQL generation fails even though the SQL itself is correct

## Why Option 1 Falls Back to Legacy

Option 1's enhanced SQL generator (`sql_generate_v2.py`) is likely failing for some reason (possibly also JSON parsing or schema retrieval), causing it to fall back to the legacy SQL generator (`sql_generate.py`). The legacy generator then generates correct SQL but fails to parse it.

## Fix Applied

### 1. Fixed Legacy SQL Generator (`sql_generate.py`)

Added markdown code block extraction before JSON parsing:

```python
# Extract JSON if wrapped in markdown code blocks
json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
if json_match:
    content = json_match.group(1)
    logger.info("generate_sql_plan: Extracted JSON from markdown code block")

plan = json.loads(content)
```

This matches the fix already in `sql_generate_v2.py`.

### 2. Enhanced Error Logging

Added more detailed error logging to see the actual content when JSON parsing fails:

```python
except json.JSONDecodeError as e:
    logger.warning(f"generate_sql_plan: JSON decode error: {e}. Content: {content[:500]}")
```

## Expected Behavior After Fix

1. LLM generates SQL wrapped in markdown: ```json {...} ```
2. Code extracts JSON from markdown: `{...}`
3. JSON parsing succeeds
4. SQL is extracted and executed
5. Results are returned

## Testing

After restarting the server, test the query again:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is the policy rule for application with app code APP_1"}'
```

**Expected**: Should now return policy rule results.

## Why This Happens

OpenAI models (especially newer ones) often wrap JSON responses in markdown code blocks for better formatting. This is actually good practice, but our parser needs to handle it.

## Additional Investigation

While the immediate fix is in place, you should also investigate:

1. **Why is Option 1 failing?** Check logs for:
   - "Enhanced SQL: _generate_sql returned None"
   - Schema retrieval issues
   - SQL generation failures

2. **Is schema properly ingested?** Run:
   ```bash
   curl -X POST http://localhost:8000/api/ingest
   ```

3. **Check Option 1 logs** to see why it's falling back to legacy

The fix ensures that even when Option 1 falls back to legacy, the legacy generator will now work correctly.

