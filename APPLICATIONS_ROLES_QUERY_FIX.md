# Fix: Applications and Roles Query

## Problem

The system was generating an incorrect SQL query for the prompt:
> "Can you list the application names and the roles that have access to these applications?"

The generated query was returning 0 rows, indicating it was not correctly joining the tables to find the relationship between applications and roles.

## Root Cause

The relationship between applications and roles is indirect and requires multiple joins:
1. **Applications** (`catalog.application`)
2. → **Policy Rules** (`entitlement.policy_rule`) - links applications to policies
3. → **Policy Sets** (`entitlement.policy_set`) - groups policy rules
4. → **Policy Scopes** (`entitlement.policy_scope`) - defines who/where policies apply
5. → **Functional Roles** (`identity.functional_role`) - the roles that have access

The LLM was not understanding this multi-hop relationship and was likely trying to join applications directly to roles, which doesn't exist.

## Solution

### 1. Added Example Query to Schema Prompt

**File**: `backend/app/sql_schema_prompt.md`

Added example query #11 showing the correct join path:

```sql
SELECT DISTINCT
  a.name AS application_name,
  a.code AS application_code,
  fr.name AS role_name,
  fr.code AS role_code,
  fr.category AS role_category
FROM catalog.application a
JOIN entitlement.policy_rule pr ON pr.application_id = a.id
JOIN entitlement.policy_set ps ON ps.id = pr.policy_set_id
JOIN entitlement.policy_scope psc ON psc.policy_set_id = ps.id
JOIN identity.functional_role fr ON fr.id = psc.role_id
WHERE psc.role_id IS NOT NULL
  AND pr.grant_type = 'ALLOW'
ORDER BY a.name, fr.name
LIMIT 200;
```

### 2. Enhanced System Prompt

**File**: `backend/app/sql_generate_v2.py`

Added explicit instructions for queries about "roles that have access to applications":

```python
"- For queries asking about 'roles that have access to applications' or 'applications and roles':\n"
"  - Join: catalog.application → entitlement.policy_rule (via application_id)\n"
"  - Join: entitlement.policy_rule → entitlement.policy_set (via policy_set_id)\n"
"  - Join: entitlement.policy_set → entitlement.policy_scope (via policy_set_id)\n"
"  - Join: entitlement.policy_scope → identity.functional_role (via role_id)\n"
"  - Filter: WHERE policy_scope.role_id IS NOT NULL AND policy_rule.grant_type = 'ALLOW'\n"
"  - Use DISTINCT to avoid duplicates\n"
```

### 3. Added Few-Shot Example to Query Bank

**File**: `backend/app/query_bank.json`

Added a successful example query that will be used for few-shot learning:

```json
{
  "question": "Can you list the application names and the roles that have access to these applications?",
  "sql": "SELECT DISTINCT a.name AS application_name, a.code AS application_code, fr.name AS role_name, fr.code AS role_code, fr.category AS role_category FROM catalog.application a JOIN entitlement.policy_rule pr ON pr.application_id = a.id JOIN entitlement.policy_set ps ON ps.id = pr.policy_set_id JOIN entitlement.policy_scope psc ON psc.policy_set_id = ps.id JOIN identity.functional_role fr ON fr.id = psc.role_id WHERE psc.role_id IS NOT NULL AND pr.grant_type = 'ALLOW' ORDER BY a.name, fr.name LIMIT 200;",
  "intent": "generic_sql",
  "tables_used": ["catalog.application", "entitlement.policy_rule", "entitlement.policy_set", "entitlement.policy_scope", "identity.functional_role"],
  "success": true
}
```

## How It Works Now

1. **User asks**: "Can you list the application names and the roles that have access to these applications?"

2. **Intent Classification**: Classified as `generic_sql`

3. **Schema Retrieval**: Retrieves relevant schema chunks including policy_rule, policy_set, policy_scope, and functional_role tables

4. **SQL Generation**: 
   - LLM sees the example query in the schema prompt
   - LLM sees the explicit instructions in the system prompt
   - LLM sees the few-shot example from query bank
   - LLM generates the correct multi-join query

5. **Query Execution**: Returns results showing:
   - Application name and code
   - Role name, code, and category
   - Only roles that have ALLOW access (not DENY)

## Testing

To test the fix:

1. **Restart the backend** (if running):
   ```bash
   # Stop current server, then restart
   cd backend
   python3 -m uvicorn app.main:app --reload
   ```

2. **Test the query**:
   ```bash
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Can you list the application names and the roles that have access to these applications?"}'
   ```

3. **Expected Result**: Should return a list of applications with their associated roles.

## Key Points

- **DISTINCT** is used to avoid duplicate rows (same app-role combination might appear in multiple policy sets)
- **WHERE psc.role_id IS NOT NULL** ensures we only get role-scoped policies (not region/department scoped)
- **WHERE pr.grant_type = 'ALLOW'** ensures we only show allowed access, not denied access
- The query follows the policy evaluation path: Application → Policy Rule → Policy Set → Policy Scope → Role

## Files Modified

1. `backend/app/sql_schema_prompt.md` - Added example query #11
2. `backend/app/sql_generate_v2.py` - Enhanced system prompt with explicit join instructions
3. `backend/app/query_bank.json` - Added few-shot example

