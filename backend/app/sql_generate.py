import json
import logging
import re
from pathlib import Path

from openai import OpenAI

from app.config import settings
from app.token_tracker import extract_usage_from_response, log_token_usage
from app.db import get_conn


logger = logging.getLogger("entitlements-chat.sql_generate")


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in backend/.env (OPENAI_API_KEY=...)"
        )
    return OpenAI(api_key=settings.openai_api_key)


_SCHEMA_PROMPT = Path(__file__).with_name("sql_schema_prompt.md").read_text(
    encoding="utf-8"
)


def generate_sql_plan(question: str) -> dict | None:
    """
    Ask OpenAI to decide if SQL is needed and, if so, to generate a single SELECT query.
    Returns a dict like:
      { "mode": "sql", "sql": "...", "reasoning": "..." }
    or None if the model decides SQL is not appropriate.
    """
    system = (
        "You are a SQL planner for the Entitlements Platform.\n"
        "You receive a natural language question and a schema summary.\n"
        "Your job is to decide if the question should be answered using SQL and,\n"
        "if yes, generate ONE safe SELECT statement over the given schema.\n\n"
        "Rules:\n"
        "- Only SELECT statements (no INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE).\n"
        "- Use the provided schema and examples as guidance.\n"
        "- Always include a LIMIT (e.g. 100 or 200) for list-style queries.\n"
        "- Prefer using codes like 'APP_1', 'DEPT_1' etc. when referring to apps/departments.\n"
        "- If SQL is not needed (pure documentation question), return mode='none'.\n"
        "- Respond ONLY with a compact JSON object with keys: mode, sql, reasoning.\n"
    )

    user = {
        "question": question,
        "schema": _SCHEMA_PROMPT[:12000],  # keep under typical context limits
    }

    client = _client()

    # Use chat.completions for compatibility
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(user),
            },
        ],
        temperature=0.2,
    )
    
    # Track token usage and cost
    usage = extract_usage_from_response(resp.usage, model=settings.openai_model)
    if usage:
        log_token_usage(usage, context="legacy_sql_generation")
    
    content = (resp.choices[0].message.content or "").strip()
    logger.info("generate_sql_plan raw LLM content: %s", content)

    # Try to parse JSON response
    try:
        # Extract JSON if wrapped in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
            logger.info("generate_sql_plan: Extracted JSON from markdown code block")
        
        plan = json.loads(content)
        if not isinstance(plan, dict):
            logger.warning("generate_sql_plan: non-dict JSON: %s", type(plan))
            return None
    except json.JSONDecodeError as e:
        logger.warning(f"generate_sql_plan: JSON decode error: {e}. Content: {content[:500]}")
        return None

    mode = plan.get("mode")
    sql = plan.get("sql")
    if not sql or not isinstance(sql, str):
        logger.info("generate_sql_plan: missing sql in plan: %s", plan)
        return None

    # Basic safety checks
    low = sql.lower().strip()
    if not low.startswith("select"):
        logger.info("generate_sql_plan: sql does not start with SELECT: %s", sql)
        return None
    banned = ["insert", "update", "delete", "drop", "alter", "truncate"]
    if any(b in low for b in banned):
        logger.info("generate_sql_plan: banned keyword in sql: %s", sql)
        return None

    # Ensure there is a LIMIT; if not, append a default
    # Check for LIMIT more carefully (handle newlines, case-insensitive)
    has_limit = re.search(r'\blimit\s+\d+', low, re.IGNORECASE)
    if not has_limit:
        sql = sql.rstrip(" ;") + " LIMIT 200"
        logger.info("generate_sql_plan: Added LIMIT 200 (was missing)")
    else:
        logger.info("generate_sql_plan: SQL already has LIMIT clause")

    logger.info("generate_sql_plan: accepted sql: %s", sql)
    return {"mode": mode, "sql": sql, "reasoning": plan.get("reasoning", "")}


def run_sql_plan(plan: dict) -> dict:
    """
    Execute the generated SQL in a read-only fashion.
    Returns dict with sql + rows (capped) + row_count.
    """
    sql = plan["sql"]
    # Final safeguard: disallow multiple statements
    # Remove semicolons inside strings first
    sql_clean = re.sub(r"';", "", sql)
    # Remove trailing semicolon (single statement terminator is OK)
    sql_clean = sql_clean.rstrip().rstrip(';')
    # Check if there are any remaining semicolons (would indicate multiple statements)
    if ";" in sql_clean:
        raise ValueError("Refusing to execute SQL with multiple statements (multiple semicolons detected)")
    
    # Remove trailing semicolon from original SQL for execution
    sql = sql.rstrip().rstrip(';')

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    # Limit preview rows for prompt
    preview = rows[:25]
    logger.info("run_sql_plan: executed sql with row_count=%s", len(rows))
    return {
        "kind": "generic_sql",
        "sql": sql,
        "rows": rows,
        "preview": preview,
        "row_count": len(rows),
        "reasoning": plan.get("reasoning", ""),
    }


