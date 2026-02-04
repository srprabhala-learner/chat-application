# Adding New Capabilities to the Chat Application

This guide demonstrates how to add new intent+template combinations to extend the chat application's capabilities. We'll use the `apps_for_dept` example to show the complete pattern.

## Overview

The chat application uses a three-step approach:
1. **Intent Classification**: Uses OpenAI to classify user questions into predefined intents
2. **Template Execution**: Maps intents to SQL templates from `sql_templates.json`
3. **Response Generation**: Uses the SQL results to generate natural language answers

## Step-by-Step: Adding `apps_for_dept`

### Step 1: Add SQL Template to `sql_templates.json`

Add a new entry in `backend/app/sql_templates.json`:

```json
"apps_for_dept": {
  "description": "Applications available to a given department.",
  "sql": "SELECT DISTINCT\n  a.code AS app_code,\n  a.name AS app_name,\n  a.criticality,\n  a.lifecycle_state,\n  aa.availability_status,\n  r.code AS region_code\nFROM catalog.application a\nJOIN catalog.application_availability aa ON aa.application_id = a.id\nJOIN core.organization_unit ou ON ou.id = aa.organization_unit_id\nLEFT JOIN core.region r ON r.id = ou.region_id\nWHERE ou.code = %(dept_code)s\n  AND aa.availability_status = 'AVAILABLE'\n  AND (aa.effective_to IS NULL OR aa.effective_to >= CURRENT_DATE)\nORDER BY a.code\nLIMIT 200;"
}
```

**Key points:**
- Use `%(param_name)s` for parameterized queries (prevents SQL injection)
- Include a clear `description` for documentation
- Always use `LIMIT` to prevent large result sets
- Filter by `availability_status = 'AVAILABLE'` and check `effective_to` dates for active records

### Step 2: Add Intent to `intent_router.py`

#### 2a. Add to INTENTS list:

```python
INTENTS = [
    # ... existing intents ...
    "apps_for_dept",           # e.g. 'Which applications are available to DEPT_5'
    # ... rest of intents ...
]
```

#### 2b. Update the system prompt to include the new intent:

```python
"Allowed intents:\n"
"  - apps_for_dept: questions about which applications are available to a department\n"
```

#### 2c. Add training examples:

```python
{
    "question": "Which applications are available to Department 5?",
    "result": {
        "intent": "apps_for_dept",
        "dept_code": "DEPT_5",
    },
},
{
    "question": "What apps can DEPT_3 access?",
    "result": {
        "intent": "apps_for_dept",
        "dept_code": "DEPT_3",
    },
},
```

**Key points:**
- Provide 2-3 diverse examples showing different phrasings
- Ensure the `result` includes all required parameters (e.g., `dept_code`)
- Normalize codes (e.g., "Department 5" → "DEPT_5", "App 3" → "APP_3")

### Step 3: Wire Intent to Template in `main.py`

Add the intent to the `template_intents` dictionary:

```python
template_intents = {
    # ... existing mappings ...
    "apps_for_dept": ("apps_for_dept", lambda i: {"dept_code": i.get("dept_code")}),
    # ... rest of mappings ...
}
```

**Key points:**
- First value: template name (must match key in `sql_templates.json`)
- Second value: lambda function that extracts parameters from `intent_info`
- The lambda should return a dict with all parameters required by the SQL template

### Step 4: Test

Test with various phrasings:
- "Which applications are available to Department 5?"
- "What apps can DEPT_3 access?"
- "Show me all apps for dept 10"

## Pattern Summary

For any new capability, follow this pattern:

1. **Define SQL Template** (`sql_templates.json`):
   - Write parameterized SQL query
   - Add description

2. **Add Intent** (`intent_router.py`):
   - Add to `INTENTS` list
   - Update system prompt
   - Add 2-3 training examples

3. **Wire Up** (`main.py`):
   - Add entry to `template_intents` dictionary
   - Map intent → (template_name, params_builder)

4. **Test**:
   - Try different phrasings
   - Verify parameter extraction (check logs)
   - Verify SQL execution (check logs)

## Example: Adding `regions_for_app`

Here's a complete example for a new capability:

### 1. SQL Template (`sql_templates.json`):
```json
"regions_for_app": {
  "description": "Regions where a given application is available.",
  "sql": "SELECT DISTINCT\n  r.code AS region_code,\n  r.name AS region_name\nFROM catalog.application a\nJOIN catalog.application_availability aa ON aa.application_id = a.id\nJOIN core.organization_unit ou ON ou.id = aa.organization_unit_id\nJOIN core.region r ON r.id = ou.region_id\nWHERE a.code = %(app_code)s\n  AND aa.availability_status = 'AVAILABLE'\n  AND (aa.effective_to IS NULL OR aa.effective_to >= CURRENT_DATE)\nORDER BY r.code\nLIMIT 200;"
}
```

### 2. Intent Router (`intent_router.py`):
```python
# In INTENTS list:
"regions_for_app",     # e.g. 'Which regions have access to APP_1'

# In system prompt:
"  - regions_for_app: questions about which regions have access to an application\n"

# In examples:
{
    "question": "Which regions have access to Application 1?",
    "result": {
        "intent": "regions_for_app",
        "app_code": "APP_1",
    },
},
```

### 3. Main Router (`main.py`):
```python
# In template_intents:
"regions_for_app": ("regions_for_app", lambda i: {"app_code": i.get("app_code")}),
```

That's it! The system will automatically:
- Classify the question
- Extract parameters
- Execute the SQL template
- Generate a natural language response

## Best Practices

1. **SQL Templates**:
   - Always use parameterized queries (`%(param)s`)
   - Include `LIMIT` clauses
   - Filter for active/available records
   - Use `DISTINCT` when appropriate
   - Join through proper relationships

2. **Intent Examples**:
   - Include 2-3 examples per intent
   - Vary the phrasing (formal, casual, abbreviated)
   - Ensure parameter extraction works (check normalization)

3. **Parameter Extraction**:
   - The intent classifier normalizes codes automatically
   - "Application 3" → "APP_3"
   - "Department 5" → "DEPT_5"
   - "Dept 10" → "DEPT_10"

4. **Testing**:
   - Test with exact matches from examples
   - Test with variations
   - Check logs for intent classification
   - Check logs for SQL execution
   - Verify results match database state

## Troubleshooting

**Intent not being classified correctly:**
- Add more examples to `intent_router.py`
- Check the system prompt description
- Verify the intent name matches in all places

**SQL execution fails:**
- Check parameter names match between template and params_builder
- Verify SQL syntax (test in psql first)
- Check for NULL parameter values

**No results returned:**
- Verify data exists in database
- Check SQL WHERE clauses
- Verify date filters (`effective_to`)

