# Fix for Policy Rule Queries

## Problem

The system was unable to query policy rules for applications. Query:
```
"what is the policy rule for application with app code APP_1"
```

Expected: Should return policy rules from `entitlement.policy_rule` table where `application_id` matches the application with code `APP_1`.

## Root Cause

The `entitlement.policy_rule` table was **not documented** in the `sql_schema_prompt.md` file, which is used as the schema context for SQL generation. The LLM didn't know about this table, so it couldn't generate the correct SQL.

## Fixes Applied

### 1. Added Policy Rule Table to Schema Prompt

Updated `backend/app/sql_schema_prompt.md` to include:

- **`entitlement.policy_rule`** table documentation:
  - `id` (PK)
  - `policy_set_id` → `entitlement.policy_set.id`
  - `application_id` → `catalog.application.id` (KEY relationship)
  - `module_id`, `feature_id` (optional)
  - `grant_type` (ALLOW, DENY)
  - `priority` (INT)
  - `condition_logic` (TEXT) - the rule expression
  - `created_at`

- **`entitlement.policy_set`** table documentation

- **Example query** showing how to join policy_rule with application:
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

### 2. Added Policy Query Examples to Intent Router

Added examples to `intent_router.py`:
- "What is the policy rule for application with app code APP_1?"
- "Show me the policy rules for APP_2"

These help the intent classifier recognize policy queries as `generic_sql` (not `knowledge_only`).

### 3. Enhanced SQL Generation Prompt

Updated `sql_generate_v2.py` to include:
- Explicit instruction: "For policy-related queries: join entitlement.policy_rule with catalog.application on application_id = application.id, then filter by application.code."
- Example policy query in the prompt

## Expected SQL

For the query "what is the policy rule for application with app code APP_1", the system should now generate:

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

This will return the policy rule record:
```
id: 181
policy_set_id: 4
application_id: 301
grant_type: ALLOW
priority: 100
condition_logic: ROLE_CATEGORY = 'SALES'
created_at: 2026-01-28 22:05:03.411 +0530
```

## Testing

### 1. Re-run Ingestion (Important!)

The schema prompt is used during ingestion. Re-run ingestion to ensure the updated schema is stored:

```bash
curl -X POST http://localhost:8000/api/ingest
```

### 2. Test Policy Query

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is the policy rule for application with app code APP_1"}'
```

### 3. Verify Results

The response should include:
- Policy rule ID
- Application ID (should be 301 for APP_1)
- Grant type (ALLOW/DENY)
- Priority
- Condition logic (e.g., "ROLE_CATEGORY = 'SALES'")
- Created timestamp

## Additional Policy Queries

The system should now handle various policy-related queries:

- "What are the policy rules for APP_1?"
- "Show me all policies for application APP_2"
- "What is the grant type for policy rule 181?"
- "List all policy rules with ALLOW grant type"

## Schema Parser Note

The schema parser (`schema_parser.py`) may not extract all columns perfectly, but this is okay because:
1. The `sql_schema_prompt.md` file provides the complete schema documentation
2. The fallback mechanism uses the full schema prompt if retrieval fails
3. The LLM uses the schema prompt as the primary source of truth

## Files Modified

1. `backend/app/sql_schema_prompt.md` - Added policy_rule and policy_set tables
2. `backend/app/intent_router.py` - Added policy query examples
3. `backend/app/sql_generate_v2.py` - Added policy-specific instructions

## Next Steps

1. **Re-run ingestion** to update the schema context
2. **Test the query** to verify it works
3. **Check logs** if it still fails to see where the issue is
4. **Add to query bank** if successful (will happen automatically)

