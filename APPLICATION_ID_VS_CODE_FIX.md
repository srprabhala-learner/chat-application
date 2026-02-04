# Fix: Application ID vs Application Code Queries

## Problem

The system was unable to handle queries that reference applications by **numeric ID** instead of **code**.

**Example failing query:**
```
"what is the policy rule for the application id 301"
```

**Root Cause:**
- All schema examples used application **codes** (e.g., `WHERE a.code = 'APP_1'`)
- SQL generation prompt instructed to "prefer using codes"
- No examples or instructions for handling numeric **IDs** (e.g., `WHERE a.id = 301`)

## Fix Applied

### 1. Updated Schema Prompt (`sql_schema_prompt.md`)

**Added explicit examples for both ID and code queries:**

- **Example 5** now shows:
  - Query by code: `WHERE a.code = 'APP_1'`
  - Query by ID: `WHERE pr.application_id = 301`
  - Direct filter option: `WHERE pr.application_id = 301` (without join if not needed)

**Added to Rules section:**
- Clear instructions on when to use ID vs code:
  - "application code APP_1" → use `WHERE a.code = 'APP_1'`
  - "application id 301" or "application ID 301" → use `WHERE a.id = 301` or `WHERE pr.application_id = 301`
  - Numeric values usually mean ID, text like "APP_1" means code

### 2. Updated SQL Generation Prompt (`sql_generate_v2.py`)

**Added explicit instructions:**
```
- **Application References**:
  - If user says 'application code APP_1': use WHERE a.code = 'APP_1'
  - If user says 'application id 301' or 'application ID 301': use WHERE a.id = 301 or WHERE pr.application_id = 301
  - For policy_rule queries with application ID, you can filter directly: WHERE pr.application_id = 301
```

**Added example for ID-based policy query:**
```json
{"mode":"sql","sql":"SELECT pr.id, pr.policy_set_id, pr.application_id, pr.grant_type, pr.priority, pr.condition_logic FROM entitlement.policy_rule pr WHERE pr.application_id = 301 LIMIT 200;","reasoning":"Querying policy rules for application ID 301"}
```

### 3. Updated Intent Router (`intent_router.py`)

**Added example for ID-based queries:**
- "What is the policy rule for application id 301?" → classified as `generic_sql`

## Expected Behavior

### Query: "what is the policy rule for the application id 301"

**Should generate:**
```sql
SELECT 
  pr.id,
  pr.policy_set_id,
  pr.application_id,
  pr.grant_type,
  pr.priority,
  pr.condition_logic,
  pr.created_at
FROM entitlement.policy_rule pr
WHERE pr.application_id = 301
ORDER BY pr.priority, pr.id
LIMIT 200;
```

**Or with application details:**
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
WHERE pr.application_id = 301
ORDER BY pr.priority, pr.id
LIMIT 200;
```

## Testing

### 1. Re-run Ingestion

```bash
curl -X POST http://localhost:8000/api/ingest
```

### 2. Test ID-based Query

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is the policy rule for the application id 301"}'
```

### 3. Test Code-based Query (should still work)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is the policy rule for application with app code APP_1"}'
```

## Key Differences

| Query Type | Filter | Example |
|------------|--------|---------|
| **By Code** | `WHERE a.code = 'APP_1'` | "app code APP_1", "application APP_1" |
| **By ID** | `WHERE pr.application_id = 301` | "application id 301", "application ID 301", "application 301" (numeric) |

## Additional Notes

1. **Direct Filter**: For policy_rule queries with application ID, you can filter directly on `pr.application_id` without joining to `catalog.application` unless you need application details (code, name, etc.).

2. **Context Matters**: If user says "application 301" without "code" or "id", the system should interpret:
   - Numeric value (301) → ID
   - Text value (APP_1) → Code

3. **Efficiency**: Direct filtering on `pr.application_id = 301` is more efficient than joining when you only need policy rule data.

## Files Modified

1. `backend/app/sql_schema_prompt.md` - Added ID vs code examples and rules
2. `backend/app/sql_generate_v2.py` - Added ID handling instructions and examples
3. `backend/app/intent_router.py` - Added ID-based query example

## Verification

After re-running ingestion, the system should now correctly handle:
- ✅ "what is the policy rule for application id 301"
- ✅ "show policy rules for application ID 301"
- ✅ "what is the policy rule for application with app code APP_1" (still works)
- ✅ "policy rules for APP_1" (still works)

