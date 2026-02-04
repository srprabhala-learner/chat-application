## Entitlements Platform - SQL Schema Summary (for Text-to-SQL)

Use this as your mental model of the database when generating SQL.
All queries MUST be read-only (SELECT) and should LIMIT rows (e.g. 100–200).

---

### Core Dimensions

#### 0) Tenants

- **`core.tenant`**
  - `id` (PK)
  - `code` (VARCHAR, UNIQUE)
  - `name` (VARCHAR)
  - `status` (VARCHAR, default 'ACTIVE')
  - `created_at`, `updated_at` (TIMESTAMPTZ)

Purpose: Root tenant/organization table. Most other tables reference `tenant_id`.

---

#### 1) Applications

- **`catalog.application`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (e.g. `APP_1`)
  - `name`
  - `description`
  - `category_id` → `catalog.application_category.id`
  - `criticality` (e.g. `BUSINESS_CRITICAL`, `SUPPORTING`, `EXPERIMENTAL`)
  - `lifecycle_state` (e.g. `ACTIVE`, `PILOT`, `SUNSET`)
  - `owner_org_unit_id` → `core.organization_unit.id`

- **`catalog.application_category`**
  - `id` (PK)
  - `code` (e.g. `BUSINESS`, `INFRA`)
  - `name`

---

#### 2) Regions & Countries

- **`core.region`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (e.g. `AMER`, `EMEA`, `APAC`)
  - `name`

- **`core.country`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `iso_code` (e.g. `US`, `DE`)
  - `name`
  - `region_id` → `core.region.id`

---

#### 3) Organization Units (Departments)

- **`core.organization_unit`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (e.g. `ACME_ROOT`, `ACME_AMER`, `DEPT_1`, `DEPT_2`)
  - `name`
  - `type_id` → `core.organization_unit_type.id` (values like `COMPANY`, `REGION`, `DEPARTMENT`, `TEAM`)
  - `parent_id` → `core.organization_unit.id` (hierarchy)
  - `region_id` → `core.region.id`
  - `country_id` → `core.country.id`

Typical usage:
- Departments are those with `code` like `DEPT_%` and type `DEPARTMENT`.

---

#### 4) Users

- **`identity.user_account`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `username` (e.g. `user00001`)
  - `email`
  - `first_name`, `last_name`
  - `primary_org_unit_id` → `core.organization_unit.id` (user's home department)
  - `employment_type` (e.g. `FTE`, `CONTRACTOR`, `INTERN`)
  - `seniority_level` (e.g. `JUNIOR`, `MID`, `SENIOR`, `MANAGER`, `DIRECTOR`)
  - `status` (usually `ACTIVE`)

- **`identity.user_attribute`**
  - `id` (PK)
  - `user_id` → `identity.user_account.id`
  - `key` (VARCHAR) - attribute key
  - `value` (TEXT) - attribute value

Joins:
- To get the user's department:
  - `identity.user_account.primary_org_unit_id` → `core.organization_unit.id`
- To get the user's region:
  - join to `core.organization_unit`, then `core.organization_unit.region_id` → `core.region.id`

#### 4a) Roles

- **`identity.functional_role`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (VARCHAR, e.g. `SALES_MANAGER`, `IT_ADMIN`)
  - `name` (VARCHAR)
  - `description` (TEXT)
  - `category` (VARCHAR, e.g. `SALES`, `HR`, `IT`, `FINANCE`)
  - `is_managerial` (BOOLEAN)

- **`identity.user_role_assignment`**
  - `id` (PK)
  - `user_id` → `identity.user_account.id`
  - `role_id` → `identity.functional_role.id`
  - `organization_unit_id` → `core.organization_unit.id` (optional, scoped to department)
  - `effective_from`, `effective_to` (DATE)
  - `source` (VARCHAR, e.g. `MANUAL`, `HR_SYSTEM`, `SYNC`)

Example: Find roles for a user:
```sql
SELECT 
  fr.code AS role_code,
  fr.name AS role_name,
  fr.category,
  ura.effective_from,
  ura.effective_to
FROM identity.user_role_assignment ura
JOIN identity.functional_role fr ON fr.id = ura.role_id
JOIN identity.user_account u ON u.id = ura.user_id
WHERE u.username = 'user00001'
  AND (ura.effective_to IS NULL OR ura.effective_to >= CURRENT_DATE)
ORDER BY fr.category, fr.code
LIMIT 200;
```

#### 4b) Groups

- **`identity.group_ref`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (VARCHAR)
  - `name` (VARCHAR)
  - `description` (TEXT)
  - `group_type` (VARCHAR, `STATIC` or `DYNAMIC`)

- **`identity.group_membership`**
  - `id` (PK)
  - `group_id` → `identity.group_ref.id`
  - `user_id` → `identity.user_account.id`
  - `added_at` (TIMESTAMPTZ)
  - `added_by` (VARCHAR)

Example: Find groups for a user:
```sql
SELECT 
  gr.code AS group_code,
  gr.name AS group_name,
  gr.group_type,
  gm.added_at
FROM identity.group_membership gm
JOIN identity.group_ref gr ON gr.id = gm.group_id
JOIN identity.user_account u ON u.id = gm.user_id
WHERE u.username = 'user00001'
ORDER BY gr.code
LIMIT 200;
```

---

### Application Deployment & Availability

#### 5) Application Instances (deployment per region)

- **`catalog.application_instance`**
  - `id` (PK)
  - `application_id` → `catalog.application.id`
  - `region_id` → `core.region.id`
  - `country_id` → `core.country.id` (optional)
  - `base_url`
  - `environment` (e.g. `PROD`, `UAT`, `DEV`)
  - `is_active` (boolean)

Purpose:
- Tells you where the application is deployed (region + environment).

#### 5a) Application Modules & Features

- **`catalog.module`**
  - `id` (PK)
  - `application_id` → `catalog.application.id`
  - `code` (VARCHAR)
  - `name` (VARCHAR)
  - `description` (TEXT)
  - `is_core` (BOOLEAN)

- **`catalog.feature`**
  - `id` (PK)
  - `module_id` → `catalog.module.id`
  - `code` (VARCHAR)
  - `name` (VARCHAR)
  - `description` (TEXT)
  - `risk_level` (VARCHAR, e.g. `LOW`, `MEDIUM`, `HIGH`)

Example: Find modules and features for an application:
```sql
SELECT 
  a.code AS app_code,
  m.code AS module_code,
  m.name AS module_name,
  f.code AS feature_code,
  f.name AS feature_name,
  f.risk_level
FROM catalog.application a
JOIN catalog.module m ON m.application_id = a.id
LEFT JOIN catalog.feature f ON f.module_id = m.id
WHERE a.code = 'APP_1'
ORDER BY m.code, f.code
LIMIT 200;
```

- **`catalog.feature_flag`**
  - `id` (PK)
  - `application_id` → `catalog.application.id`
  - `code` (VARCHAR)
  - `name` (VARCHAR)
  - `description` (TEXT)
  - `default_state` (BOOLEAN)

#### 6) Application Availability (which regions/departments can access)

- **`catalog.application_availability`**
  - `id` (PK)
  - `application_id` → `catalog.application.id`
  - `region_id` → `core.region.id` (optional)
  - `organization_unit_type_id` → `core.organization_unit_type.id` (optional)
  - `organization_unit_id` → `core.organization_unit.id` (optional, typically a department)
  - `effective_from`, `effective_to` (date range)
  - `availability_status` (e.g. `AVAILABLE`, `NOT_AVAILABLE`, `PILOT`)

Common patterns:
- **All departments in a region**:
  - `application_availability.region_id` is set, `organization_unit_id` is NULL.
- **Specific department**:
  - `organization_unit_id` is set (e.g. to `DEPT_1`’s `id`).

Useful filters:
- Only currently valid rules:
  - `availability_status = 'AVAILABLE'`
  - `effective_to IS NULL OR effective_to >= CURRENT_DATE`

Joins:
- From app to departments that can access it:
  ```sql
  SELECT DISTINCT
    ou.code AS department_code,
    ou.name AS department_name,
    r.code  AS region_code,
    aa.availability_status
  FROM catalog.application a
  JOIN catalog.application_availability aa ON aa.application_id = a.id
  JOIN core.organization_unit ou ON ou.id = aa.organization_unit_id
  LEFT JOIN core.region r ON r.id = ou.region_id
  WHERE a.code = 'APP_1'
    AND aa.availability_status = 'AVAILABLE'
    AND (aa.effective_to IS NULL OR aa.effective_to >= CURRENT_DATE);
  ```

---

### Entitlements (User → Application)

#### 7) User-level Entitlements

- **`entitlement.user_entitlement`**
  - `id` (PK)
  - `user_id` → `identity.user_account.id`
  - `application_id` → `catalog.application.id`
  - `application_instance_id` → `catalog.application_instance.id` (optional)
  - `grant_source` (e.g. `POLICY`, `EXCEPTION`, `GROUP`, `ROLE`)
  - `status` (`ACTIVE`, `EXPIRED`, `REVOKED`)
  - `effective_from`, `effective_to`

Use this when the question is specifically about **user-to-application grants**.

#### 8) Policy Rules

- **`entitlement.policy_rule`**
  - `id` (PK)
  - `policy_set_id` → `entitlement.policy_set.id`
  - `application_id` → `catalog.application.id` (KEY: links to application)
  - `module_id` → `catalog.module.id` (optional)
  - `feature_id` → `catalog.feature.id` (optional)
  - `grant_type` (e.g. `ALLOW`, `DENY`)
  - `priority` (INT, default 100)
  - `condition_logic` (TEXT) - the rule condition/expression (e.g. `ROLE_CATEGORY = 'SALES'`)
  - `created_at` (TIMESTAMPTZ)

**Important**: To find policy rules for an application:
- Join `entitlement.policy_rule` with `catalog.application` on `application_id = application.id`
- Filter by `application.code` (e.g. `'APP_1'`)
- The `condition_logic` column contains the rule expression

Example query:
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

- **`entitlement.policy_set`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (VARCHAR)
  - `name` (VARCHAR)
  - `description` (TEXT)
  - `priority` (INT)
  - `is_active` (BOOLEAN)

- **`entitlement.policy_scope`**
  - `id` (PK)
  - `policy_set_id` → `entitlement.policy_set.id`
  - `region_id` → `core.region.id` (optional)
  - `country_id` → `core.country.id` (optional)
  - `organization_unit_id` → `core.organization_unit.id` (optional)
  - `role_id` → `identity.functional_role.id` (optional)
  - `group_id` → `identity.group_ref.id` (optional)

Purpose: Defines the scope (who/where) a policy set applies to.

#### 8a) Permissions

- **`entitlement.permission`**
  - `id` (PK)
  - `code` (VARCHAR, UNIQUE)
  - `name` (VARCHAR)
  - `description` (TEXT)

- **`entitlement.application_permission`**
  - `id` (PK)
  - `application_id` → `catalog.application.id`
  - `permission_id` → `entitlement.permission.id`
  - `feature_id` → `catalog.feature.id` (optional)

Example: Find permissions for an application:
```sql
SELECT 
  a.code AS app_code,
  p.code AS permission_code,
  p.name AS permission_name,
  f.code AS feature_code
FROM catalog.application a
JOIN entitlement.application_permission ap ON ap.application_id = a.id
JOIN entitlement.permission p ON p.id = ap.permission_id
LEFT JOIN catalog.feature f ON f.id = ap.feature_id
WHERE a.code = 'APP_1'
ORDER BY p.code
LIMIT 200;
```

- **`entitlement.user_permission`**
  - `id` (PK)
  - `user_entitlement_id` → `entitlement.user_entitlement.id`
  - `permission_id` → `entitlement.permission.id`
  - `grant_type` (VARCHAR, default `ALLOW`)

#### 8b) Policy Conditions

- **`entitlement.policy_condition`**
  - `id` (PK)
  - `policy_rule_id` → `entitlement.policy_rule.id`
  - `attribute_id` → `entitlement.condition_attribute_ref.id`
  - `operator_id` → `entitlement.condition_operator_ref.id`
  - `value` (TEXT)
  - `conjunction` (VARCHAR, default `AND`)
  - `condition_order` (INT)

Purpose: Detailed conditions for policy rules (alternative to `condition_logic` text field).

#### 8c) Toxic Combinations

- **`entitlement.toxic_combination`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `code` (VARCHAR)
  - `description` (TEXT)
  - `is_blocking` (BOOLEAN, default TRUE)

- **`entitlement.toxic_combination_member`**
  - `id` (PK)
  - `toxic_combination_id` → `entitlement.toxic_combination.id`
  - `application_id` → `catalog.application.id`
  - `permission_id` → `entitlement.permission.id` (optional)

Purpose: Defines combinations of applications/permissions that should not be granted together.

Example: Find toxic combinations for an application:
```sql
SELECT 
  tc.code AS toxic_code,
  tc.description,
  tc.is_blocking,
  a.code AS app_code,
  p.code AS permission_code
FROM entitlement.toxic_combination tc
JOIN entitlement.toxic_combination_member tcm ON tcm.toxic_combination_id = tc.id
JOIN catalog.application a ON a.id = tcm.application_id
LEFT JOIN entitlement.permission p ON p.id = tcm.permission_id
WHERE a.code = 'APP_1'
ORDER BY tc.code
LIMIT 200;
```

Example:
```sql
SELECT
  u.username,
  u.email,
  a.code   AS app_code,
  a.name   AS app_name,
  ue.status,
  ue.effective_from,
  ue.effective_to
FROM entitlement.user_entitlement ue
JOIN identity.user_account u ON u.id = ue.user_id
JOIN catalog.application a ON a.id = ue.application_id
WHERE a.code = 'APP_1'
  AND ue.status = 'ACTIVE';
```

---

### Typical Question → Query Patterns

1. **“What is the criticality/state/status of APP_1?”**
   - Table: `catalog.application`
   - SQL:
   ```sql
   SELECT code, name, criticality, lifecycle_state
   FROM catalog.application
   WHERE code = 'APP_1';
   ```

2. **“Which departments have access to APP_1?”**
   - Tables: `catalog.application`, `catalog.application_availability`,
     `core.organization_unit`, `core.region`.
   - SQL:
   ```sql
   SELECT DISTINCT
     ou.code AS department_code,
     ou.name AS department_name,
     r.code  AS region_code,
     aa.availability_status
   FROM catalog.application a
   JOIN catalog.application_availability aa ON aa.application_id = a.id
   JOIN core.organization_unit ou ON ou.id = aa.organization_unit_id
   LEFT JOIN core.region r ON r.id = ou.region_id
   WHERE a.code = 'APP_1'
     AND aa.availability_status = 'AVAILABLE'
     AND (aa.effective_to IS NULL OR aa.effective_to >= CURRENT_DATE)
   ORDER BY r.code, ou.code
   LIMIT 200;
   ```

3. **“List users from DEPT_1 who have access to APP_1”**
   - Approach 1 (via department → availability, not per-user entitlements):
   ```sql
   SELECT DISTINCT
     u.id,
     u.username,
     u.email,
     u.first_name,
     u.last_name,
     ou.code AS department_code,
     r.code  AS region_code
   FROM identity.user_account u
   JOIN core.organization_unit ou ON ou.id = u.primary_org_unit_id
   LEFT JOIN core.region r ON r.id = ou.region_id
   JOIN catalog.application a ON a.code = 'APP_1'
   JOIN catalog.application_availability aa ON aa.application_id = a.id
     AND aa.organization_unit_id = ou.id
   WHERE ou.code = 'DEPT_1'
     AND aa.availability_status = 'AVAILABLE'
     AND (aa.effective_to IS NULL OR aa.effective_to >= CURRENT_DATE)
     AND u.status = 'ACTIVE'
   ORDER BY u.username
   LIMIT 200;
   ```

   - Approach 2 (via explicit `entitlement.user_entitlement` if you want only users with explicit grants):
   ```sql
   SELECT DISTINCT
     u.id,
     u.username,
     u.email,
     u.first_name,
     u.last_name,
     ou.code AS department_code,
     r.code  AS region_code
   FROM entitlement.user_entitlement ue
   JOIN identity.user_account u ON u.id = ue.user_id
   LEFT JOIN core.organization_unit ou ON ou.id = u.primary_org_unit_id
   LEFT JOIN core.region r ON r.id = ou.region_id
   JOIN catalog.application a ON a.id = ue.application_id
   WHERE a.code = 'APP_1'
     AND ou.code = 'DEPT_1'
     AND ue.status = 'ACTIVE'
   ORDER BY u.username
   LIMIT 200;
   ```

4. **"Which regions is APP_1 deployed in (PROD)?"**
   - Tables: `catalog.application`, `catalog.application_instance`, `core.region`.
   ```sql
   SELECT DISTINCT
     r.code AS region_code,
     r.name AS region_name,
     ai.environment,
     ai.base_url
   FROM catalog.application a
   JOIN catalog.application_instance ai ON ai.application_id = a.id
   JOIN core.region r ON r.id = ai.region_id
   WHERE a.code = 'APP_1'
     AND ai.environment = 'PROD'
     AND ai.is_active = TRUE;
   ```

5. **"What is the policy rule for application with app code APP_1?"** or **"What is the policy rule for application id 301?"**
   - Tables: `entitlement.policy_rule`, `catalog.application`.
   - **IMPORTANT**: Applications can be referenced by:
     - **Code**: `WHERE a.code = 'APP_1'` (when user says "app code APP_1" or "application APP_1")
     - **ID**: `WHERE pr.application_id = 301` or `WHERE a.id = 301` (when user says "application id 301" or "application ID 301")
   
   Example using code:
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
   
   Example using ID (when user specifies numeric ID):
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
   
   **Note**: You can also filter directly on `pr.application_id` without joining to `catalog.application` if you only need policy rule data:
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

#### Example: List applications and roles that have access
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
  AND pr.grant_type = 'ALLOW'  -- Only show allowed access
ORDER BY a.name, fr.name
LIMIT 200;
```

**Important**: To find which roles have access to applications:
- Join `catalog.application` → `entitlement.policy_rule` (via `application_id`)
- Join `entitlement.policy_rule` → `entitlement.policy_set` (via `policy_set_id`)
- Join `entitlement.policy_set` → `entitlement.policy_scope` (via `policy_set_id`)
- Join `entitlement.policy_scope` → `identity.functional_role` (via `role_id`)
- Filter where `policy_scope.role_id IS NOT NULL` to get role-scoped policies

6. **"What roles does user user00001 have?"**
   - Tables: `identity.user_account`, `identity.user_role_assignment`, `identity.functional_role`.
   ```sql
   SELECT 
     fr.code AS role_code,
     fr.name AS role_name,
     fr.category,
     ura.effective_from,
     ura.effective_to
   FROM identity.user_account u
   JOIN identity.user_role_assignment ura ON ura.user_id = u.id
   JOIN identity.functional_role fr ON fr.id = ura.role_id
   WHERE u.username = 'user00001'
     AND (ura.effective_to IS NULL OR ura.effective_to >= CURRENT_DATE)
   ORDER BY fr.category, fr.code
   LIMIT 200;
   ```

7. **"Which users are in group GROUP_1?"**
   - Tables: `identity.group_ref`, `identity.group_membership`, `identity.user_account`.
   ```sql
   SELECT 
     u.username,
     u.email,
     u.first_name,
     u.last_name,
     gm.added_at
   FROM identity.group_ref gr
   JOIN identity.group_membership gm ON gm.group_id = gr.id
   JOIN identity.user_account u ON u.id = gm.user_id
   WHERE gr.code = 'GROUP_1'
   ORDER BY u.username
   LIMIT 200;
   ```

8. **"What permissions does application APP_1 have?"**
   - Tables: `catalog.application`, `entitlement.application_permission`, `entitlement.permission`.
   ```sql
   SELECT 
     p.code AS permission_code,
     p.name AS permission_name,
     f.code AS feature_code
   FROM catalog.application a
   JOIN entitlement.application_permission ap ON ap.application_id = a.id
   JOIN entitlement.permission p ON p.id = ap.permission_id
   LEFT JOIN catalog.feature f ON f.id = ap.feature_id
   WHERE a.code = 'APP_1'
   ORDER BY p.code
   LIMIT 200;
   ```

9. **"What modules and features does APP_1 have?"**
   - Tables: `catalog.application`, `catalog.module`, `catalog.feature`.
   ```sql
   SELECT 
     m.code AS module_code,
     m.name AS module_name,
     m.is_core,
     f.code AS feature_code,
     f.name AS feature_name,
     f.risk_level
   FROM catalog.application a
   JOIN catalog.module m ON m.application_id = a.id
   LEFT JOIN catalog.feature f ON f.module_id = m.id
   WHERE a.code = 'APP_1'
   ORDER BY m.code, f.code
   LIMIT 200;
   ```

10. **"What are the toxic combinations for APP_1?"**
    - Tables: `entitlement.toxic_combination`, `entitlement.toxic_combination_member`, `catalog.application`.
    ```sql
    SELECT 
      tc.code AS toxic_code,
      tc.description,
      tc.is_blocking,
      a.code AS app_code,
      p.code AS permission_code
    FROM entitlement.toxic_combination tc
    JOIN entitlement.toxic_combination_member tcm ON tcm.toxic_combination_id = tc.id
    JOIN catalog.application a ON a.id = tcm.application_id
    LEFT JOIN entitlement.permission p ON p.id = tcm.permission_id
    WHERE a.code = 'APP_1'
    ORDER BY tc.code
    LIMIT 200;
    ```

11. **"List the application names and the roles that have access to these applications"**
    - Tables: `catalog.application`, `entitlement.policy_rule`, `entitlement.policy_set`, `entitlement.policy_scope`, `identity.functional_role`.
    - **Key**: Applications are linked to roles through policy rules → policy sets → policy scopes.
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

---

### Audit & Logging

#### 9) Audit Tables

- **`audit.entitlement_change_log`**
  - `id` (PK)
  - `tenant_id` → `core.tenant.id`
  - `user_id` → `identity.user_account.id` (optional)
  - `application_id` → `catalog.application.id` (optional)
  - `change_type` (VARCHAR, e.g. `GRANT`, `REVOKE`, `UPDATE`)
  - `change_source` (VARCHAR, e.g. `POLICY_EVAL`, `ADMIN_ACTION`, `BULK_UPLOAD`, `SYNC`)
  - `change_reason` (TEXT)
  - `details` (JSONB)
  - `changed_at` (TIMESTAMPTZ)
  - `changed_by` (VARCHAR)

Example: Find entitlement changes for a user:
```sql
SELECT 
  u.username,
  a.code AS app_code,
  ecl.change_type,
  ecl.change_source,
  ecl.change_reason,
  ecl.changed_at,
  ecl.changed_by
FROM audit.entitlement_change_log ecl
LEFT JOIN identity.user_account u ON u.id = ecl.user_id
LEFT JOIN catalog.application a ON a.id = ecl.application_id
WHERE u.username = 'user00001'
ORDER BY ecl.changed_at DESC
LIMIT 200;
```

- **`audit.policy_evaluation_log`**
  - `id` (PK)
  - `user_id` → `identity.user_account.id` (optional)
  - `policy_set_id` → `entitlement.policy_set.id` (optional)
  - `evaluation_at` (TIMESTAMPTZ)
  - `input_context` (JSONB)
  - `output_decision` (JSONB)

Purpose: Logs policy evaluation decisions for debugging and auditing.

---

### Rules for SQL Generation

- Only generate **SELECT** statements.
- Never modify data (no INSERT/UPDATE/DELETE/TRUNCATE/ALTER).
- Always include a **LIMIT** (e.g., 100 or 200) for list-style queries.
- **Referencing Applications**:
  - If user mentions **"application code"** or **"app code"** or **"APP_X"**: Use `WHERE a.code = 'APP_1'`
  - If user mentions **"application id"** or **"application ID"** or a **numeric ID** (e.g., "301"): Use `WHERE a.id = 301` or `WHERE pr.application_id = 301`
  - If user says "application 301" without "code" or "id", check context: numeric values usually mean ID, text like "APP_1" means code
- **Referencing Departments**: Prefer using `code` (e.g. `'DEPT_1'`) when available, but can use `id` if user specifies numeric ID.
- When unsure between multiple valid join paths, pick the **simplest** that answers the question.
- **For policy_rule queries**: You can filter directly on `pr.application_id` if the user specifies an application ID, without needing to join to `catalog.application` unless you need application details.


