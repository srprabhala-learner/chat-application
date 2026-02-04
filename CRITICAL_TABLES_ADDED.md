# Critical Tables Added to Schema Documentation

## Summary

Added **18 critical tables** to `sql_schema_prompt.md`, bringing the total documented tables from **12 to 30** (out of 71 total tables in the database).

## Tables Added

### Core Schema (1 table)
- ✅ `core.tenant` - Root tenant/organization table

### Identity Schema (5 tables)
- ✅ `identity.user_attribute` - User attributes (key-value pairs)
- ✅ `identity.functional_role` - Functional roles (SALES, IT, etc.)
- ✅ `identity.user_role_assignment` - User-role assignments with effective dates
- ✅ `identity.group_ref` - Groups (STATIC or DYNAMIC)
- ✅ `identity.group_membership` - Group memberships

### Catalog Schema (3 tables)
- ✅ `catalog.module` - Application modules
- ✅ `catalog.feature` - Application features (within modules)
- ✅ `catalog.feature_flag` - Feature flags

### Entitlement Schema (7 tables)
- ✅ `entitlement.permission` - Permissions
- ✅ `entitlement.application_permission` - Application-permission mapping
- ✅ `entitlement.policy_scope` - Policy scopes (who/where policies apply)
- ✅ `entitlement.user_permission` - User permissions
- ✅ `entitlement.policy_condition` - Detailed policy conditions
- ✅ `entitlement.toxic_combination` - Toxic combinations
- ✅ `entitlement.toxic_combination_member` - Toxic combination members

### Audit Schema (2 tables)
- ✅ `audit.entitlement_change_log` - Entitlement change history
- ✅ `audit.policy_evaluation_log` - Policy evaluation logs

## New Query Capabilities

The system can now handle queries about:

### Roles
- "What roles does user X have?"
- "Which users have role Y?"
- "Show me all roles in category SALES"

### Groups
- "Which users are in group X?"
- "What groups does user Y belong to?"
- "List all groups"

### Permissions
- "What permissions does application APP_1 have?"
- "Which applications have permission PERM_1?"
- "What permissions does user X have for APP_1?"

### Modules & Features
- "What modules does APP_1 have?"
- "What features are in module MODULE_1?"
- "Show me all features for APP_1"

### Policy Scopes
- "What is the scope of policy set PS_1?"
- "Which policy sets apply to role ROLE_1?"

### Toxic Combinations
- "What are the toxic combinations for APP_1?"
- "Which applications cannot be granted together?"

### Audit History
- "Show me entitlement changes for user X"
- "What policy evaluations happened for user Y?"

## Example Queries Added

The schema prompt now includes 10 example query patterns (up from 5), including:
1. Application criticality/state
2. Department access
3. Users in department with app access
4. Application deployment regions
5. Policy rules for application
6. **NEW**: Roles for a user
7. **NEW**: Users in a group
8. **NEW**: Permissions for an application
9. **NEW**: Modules and features for an application
10. **NEW**: Toxic combinations for an application

## File Statistics

- **Before**: ~348 lines
- **After**: ~704 lines
- **Growth**: +356 lines (102% increase)

## Next Steps

1. **Re-run ingestion** to update the schema context:
   ```bash
   curl -X POST http://localhost:8000/api/ingest
   ```

2. **Test new query types**:
   ```bash
   # Test role queries
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What roles does user user00001 have?"}'
   
   # Test group queries
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Which users are in group GROUP_1?"}'
   
   # Test permission queries
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What permissions does application APP_1 have?"}'
   ```

3. **Monitor query bank** - Successful queries will be automatically stored for future few-shot learning

## Remaining Tables (41 tables)

Still missing but lower priority:
- Reference tables (locale_ref, currency_ref, timezone_ref, etc.)
- Configuration tables (tenant_config, global_config, etc.)
- Notification tables
- Analytics summary tables
- Employment-related tables
- Compliance and SLA tables

These can be added incrementally based on actual query needs.

