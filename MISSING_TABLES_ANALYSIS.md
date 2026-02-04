# Missing Tables Analysis

## Summary

**Total tables in database**: 71  
**Documented in schema prompt**: 12  
**Missing**: 59 tables (83% missing!)

## Missing Tables by Schema

### CORE Schema (15 missing)
- `core.tenant` - **IMPORTANT**: Root tenant table
- `core.tenant_setting` - Tenant-specific settings
- `core.tenant_config` - Tenant configuration
- `core.timezone_ref` - Timezone reference
- `core.cost_center` - Cost centers linked to org units
- `core.location` - Physical locations
- `core.tag` - Tagging system
- `core.tag_mapping` - Tag mappings
- `core.locale_ref` - Locale reference
- `core.currency_ref` - Currency reference
- `core.fiscal_calendar` - Fiscal calendar
- `core.global_config` - Global configuration
- `core.notification_channel_ref` - Notification channels
- `core.notification_template` - Notification templates
- `core.notification_preference` - Notification preferences

### IDENTITY Schema (10 missing)
- `identity.user_attribute` - User attributes
- `identity.functional_role` - **IMPORTANT**: Functional roles
- `identity.role_hierarchy` - Role hierarchy
- `identity.user_role_assignment` - **IMPORTANT**: User-role assignments
- `identity.group_ref` - Groups
- `identity.group_membership` - Group memberships
- `identity.group_dynamic_rule` - Dynamic group rules
- `identity.employment_status_ref` - Employment status reference
- `identity.job_family_ref` - Job family reference
- `identity.job_code_ref` - Job code reference
- `identity.user_employment` - User employment details

### CATALOG Schema (7 missing)
- `catalog.module` - Application modules
- `catalog.feature` - Application features
- `catalog.feature_flag` - Feature flags
- `catalog.feature_flag_target` - Feature flag targets
- `catalog.application_compliance_requirement` - Compliance requirements
- `catalog.application_data_category` - Data categories
- `catalog.application_data_category_link` - Data category links
- `catalog.application_sla` - SLA definitions

### ENTITLEMENT Schema (15 missing)
- `entitlement.permission` - Permissions
- `entitlement.application_permission` - Application-permission mapping
- `entitlement.policy_scope` - Policy scopes
- `entitlement.user_permission` - User permissions
- `entitlement.entitlement_exception_request` - Exception requests
- `entitlement.entitlement_exception_approval_step` - Approval steps
- `entitlement.toxic_combination` - Toxic combinations
- `entitlement.toxic_combination_member` - Toxic combination members
- `entitlement.condition_attribute_ref` - Condition attributes
- `entitlement.condition_operator_ref` - Condition operators
- `entitlement.policy_condition` - Policy conditions
- `entitlement.approval_workflow_template` - Approval workflows
- `entitlement.approval_workflow_step_template` - Workflow steps
- `entitlement.exception_request_workflow_link` - Workflow links
- `entitlement.access_reason_ref` - Access reasons
- `entitlement.entitlement_campaign` - Entitlement campaigns
- `entitlement.entitlement_campaign_target` - Campaign targets

### AUDIT Schema (4 missing)
- `audit.entitlement_change_log` - Change logs
- `audit.login_entitlement_snapshot` - Login snapshots
- `audit.policy_evaluation_log` - Policy evaluation logs
- `audit.notification_log` - Notification logs
- `audit.entitlement_campaign_result` - Campaign results

### ANALYTICS Schema (3 missing)
- `analytics.entitlement_summary_daily` - Daily summaries
- `analytics.application_usage_event` - Usage events
- `analytics.entitlement_health_indicator` - Health indicators

## Critical Missing Tables (High Priority)

These tables are likely to be queried frequently:

1. **`identity.functional_role`** - Roles are central to entitlements
2. **`identity.user_role_assignment`** - User-role relationships
3. **`identity.group_ref`** - Groups for access control
4. **`identity.group_membership`** - Group memberships
5. **`catalog.module`** - Application modules
6. **`catalog.feature`** - Application features
7. **`entitlement.permission`** - Permissions
8. **`entitlement.application_permission`** - App-permission mapping
9. **`entitlement.policy_scope`** - Policy scopes
10. **`entitlement.user_permission`** - User permissions
11. **`entitlement.toxic_combination`** - Toxic combinations
12. **`audit.entitlement_change_log`** - Change history
13. **`core.tenant`** - Tenant information

## Impact

Without these tables documented:
- Queries about roles, groups, permissions will fail
- Module/feature queries won't work
- Audit/history queries won't work
- Toxic combination queries won't work
- Many relationship queries will be incomplete

## Recommendation

1. **Immediate**: Add critical tables (roles, groups, permissions, modules, features)
2. **Short-term**: Add entitlement-related tables (policy_scope, user_permission, toxic_combination)
3. **Medium-term**: Add audit and analytics tables
4. **Long-term**: Add all remaining reference tables

## Next Steps

1. Update `sql_schema_prompt.md` with missing critical tables
2. Re-run ingestion to update the schema context
3. Test queries for roles, groups, permissions, etc.
4. Iteratively add more tables based on query patterns

