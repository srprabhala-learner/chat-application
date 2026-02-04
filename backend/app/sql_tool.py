import json
import re
from pathlib import Path

from app.db import get_conn


_APP_PAT = re.compile(r"\bAPP[_\-\s]?(\d+)\b", re.IGNORECASE)
_DEPT_PAT = re.compile(r"\bDEPT[_\-\s]?(\d+)\b", re.IGNORECASE)

_TEMPLATES = None


def _load_templates() -> dict:
    global _TEMPLATES
    if _TEMPLATES is None:
        cfg_path = Path(__file__).with_name("sql_templates.json")
        _TEMPLATES = json.loads(cfg_path.read_text(encoding="utf-8"))
    return _TEMPLATES


def _normalize_app_code(text: str) -> str | None:
    # Accept "Application 1" or "App1" or "APP_1"
    m = re.search(r"\bapplication\s+(\d+)\b", text, re.IGNORECASE)
    if m:
        return f"APP_{int(m.group(1))}"
    m = _APP_PAT.search(text)
    if m:
        return f"APP_{int(m.group(1))}"
    return None


def _normalize_dept_code(text: str) -> str | None:
    m = re.search(r"\bdepartment\s+(\d+)\b", text, re.IGNORECASE)
    if m:
        return f"DEPT_{int(m.group(1))}"
    m = _DEPT_PAT.search(text)
    if m:
        return f"DEPT_{int(m.group(1))}"
    return None


def maybe_run_safe_sql(question: str) -> dict | None:
    """
    Very small v1 router with allowlisted queries.
    Returns dict with {sql, params, rows} or None.
    """
    q = question.strip()
    app_code = _normalize_app_code(q)
    dept_code = _normalize_dept_code(q)

    templates = _load_templates()

    # Q1: which departments have access to application?
    if app_code and re.search(r"\bwhich\s+departments\b|\bdepartments\b.*\baccess\b", q, re.IGNORECASE):
        sql = templates["departments_for_app"]["sql"]
        params = {"app_code": app_code}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return {"kind": "departments_for_app", "sql": sql, "params": params, "rows": rows}

    # Q1b: what is the state/criticality (and related metadata) of an application?
    #      e.g. "What is the state of APP_1?", "status", "lifecycle", "criticality"
    if app_code and re.search(r"\b(criticality|state|status|lifecycle)\b", q, re.IGNORECASE):
        sql = templates["app_metadata"]["sql"]
        params = {"app_code": app_code}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return {"kind": "app_criticality", "sql": sql, "params": params, "rows": rows}

    # Q2: list users from department who have access to app (template)
    if app_code and dept_code and re.search(r"\b(users|list)\b", q, re.IGNORECASE):
        sql = templates["users_in_dept_for_app"]["sql"]
        params = {"app_code": app_code, "dept_code": dept_code}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return {"kind": "users_in_dept_for_app", "sql": sql, "params": params, "rows": rows}

    # Q3: users in a department (no specific app)
    if dept_code and re.search(r"\b(users|list|how many)\b", q, re.IGNORECASE):
        sql = templates["users_in_dept"]["sql"]
        params = {"dept_code": dept_code}
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
        return {"kind": "users_in_dept", "sql": sql, "params": params, "rows": rows}

    return None


def execute_template(template_name: str, params: dict) -> dict | None:
    """
    Execute a SQL template by name with the given parameters.
    This is the preferred way to run templated queries (vs regex-based maybe_run_safe_sql).
    
    Args:
        template_name: Key from sql_templates.json (e.g., "apps_for_dept")
        params: Dictionary of parameters for the SQL template (e.g., {"dept_code": "DEPT_5"})
    
    Returns:
        dict with {kind, sql, params, rows} or None if template not found
    """
    templates = _load_templates()
    if template_name not in templates:
        return None
    
    sql = templates[template_name]["sql"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return {
        "kind": template_name,
        "sql": sql,
        "params": params,
        "rows": rows,
    }


