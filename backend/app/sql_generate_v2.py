"""
Enhanced Text-to-SQL Generator for Option 1

Uses RAG-retrieved schema context and few-shot examples from query bank
to generate accurate SQL queries with self-validation and correction.
"""

import json
import re
import logging
import time
from typing import Dict, Optional, List

from openai import OpenAI

from app.config import settings
from app.token_tracker import extract_usage_from_response, log_token_usage
from app.db import get_conn
from app.schema_retrieval import SchemaRetriever
from app.query_bank import QueryBank

logger = logging.getLogger("entitlements-chat.sql_generate_v2")


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in backend/.env (OPENAI_API_KEY=...)"
        )
    return OpenAI(api_key=settings.openai_api_key)


class EnhancedSQLGenerator:
    """Enhanced SQL generator with schema retrieval and self-correction"""

    def __init__(self):
        self.schema_retriever = SchemaRetriever(top_k=5)
        self.query_bank = QueryBank()

    def generate_and_execute(
        self, question: str, max_retries: int = 2
    ) -> Optional[Dict]:
        """
        Generate SQL, validate, execute, and self-correct if needed.
        Returns dict with sql, rows, row_count, or None if failed.
        """
        logger.info(f"Enhanced SQL: Starting generation for question: {question}")
        
        # Retrieve relevant schema context
        schema_context = self.schema_retriever.retrieve_relevant_schema(question)
        logger.info(f"Enhanced SQL: Retrieved schema context length: {len(schema_context)} chars")
        
        # Fallback to full schema prompt if retrieval is too short or doesn't contain relevant tables
        schema_context_lower = schema_context.lower()
        question_lower = question.lower()
        
        # Check if schema context contains relevant tables for the question
        needs_policy_rule = any(word in question_lower for word in ["policy", "rule"])
        has_policy_rule = "policy_rule" in schema_context_lower or "entitlement.policy_rule" in schema_context_lower
        
        if len(schema_context) < 200 or (needs_policy_rule and not has_policy_rule):
            logger.warning(
                f"Enhanced SQL: Schema context insufficient (length: {len(schema_context)}, "
                f"needs_policy_rule: {needs_policy_rule}, has_policy_rule: {has_policy_rule}). "
                f"Using fallback schema."
            )
            from pathlib import Path
            import re
            schema_prompt_path = Path(__file__).with_name("sql_schema_prompt.md")
            if schema_prompt_path.exists():
                fallback_schema = schema_prompt_path.read_text(encoding="utf-8")
                # Use full schema if retrieval failed, otherwise append relevant sections
                if len(schema_context) < 200:
                    schema_context = fallback_schema[:8000]
                else:
                    # Append policy_rule section if missing
                    if needs_policy_rule and not has_policy_rule:
                        policy_section = ""
                        if "policy_rule" in fallback_schema.lower():
                            # Extract policy_rule section
                            policy_match = re.search(
                                r'(#### 8\) Policy Rules.*?)(?=####|\n---|\n###)',
                                fallback_schema,
                                re.DOTALL | re.IGNORECASE
                            )
                            if policy_match:
                                policy_section = policy_match.group(1)
                                schema_context = schema_context + "\n\n" + policy_section
                                logger.info(f"Enhanced SQL: Appended policy_rule section to schema context")
                logger.info(f"Enhanced SQL: Using fallback/enhanced schema, length: {len(schema_context)} chars")
        
        # Get few-shot examples
        few_shot_examples = self.query_bank.get_few_shot_examples(question, max_examples=3)
        logger.info(f"Enhanced SQL: Found {len(few_shot_examples)} few-shot examples")
        
        # Generate SQL
        sql_result = self._generate_sql(question, schema_context, few_shot_examples)
        
        if not sql_result:
            logger.error(
                f"Enhanced SQL: _generate_sql returned None for question: {question}. "
                f"Schema context length: {len(schema_context)}. "
                f"Few-shot examples: {len(few_shot_examples)}"
            )
            # Log a sample of schema context for debugging
            if schema_context:
                logger.debug(f"Enhanced SQL: Schema context sample (first 500 chars): {schema_context[:500]}")
            return None
        
        sql = sql_result["sql"]
        reasoning = sql_result.get("reasoning", "")
        
        # Validate SQL
        validation = self._validate_sql(sql)
        if not validation["valid"]:
            logger.warning(f"SQL validation failed: {validation['error']}")
            # Try to self-correct
            if max_retries > 0:
                corrected_sql = self._self_correct(
                    question, sql, validation["error"], schema_context
                )
                if corrected_sql:
                    sql = corrected_sql
                    validation = self._validate_sql(sql)
        
        if not validation["valid"]:
            logger.error(f"SQL validation failed after correction: {validation['error']}")
            return None
        
        # Execute SQL
        start_time = time.time()
        try:
            rows, row_count = self._execute_sql(sql)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Extract tables used (simple heuristic)
            tables_used = self._extract_tables_from_sql(sql)
            
            # Store in query bank
            self.query_bank.add_example(
                question=question,
                sql=sql,
                intent="generic_sql",
                tables_used=tables_used,
                success=True,
                execution_time_ms=execution_time_ms,
                row_count=row_count,
            )
            
            return {
                "kind": "enhanced_sql",
                "sql": sql,
                "reasoning": reasoning,
                "rows": rows,
                "row_count": row_count,
                "preview": rows[:25],
                "tables_used": tables_used,
                "execution_time_ms": execution_time_ms,
            }
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"SQL execution failed: {error_msg}")
            
            # Store failed example
            tables_used = self._extract_tables_from_sql(sql)
            self.query_bank.add_example(
                question=question,
                sql=sql,
                intent="generic_sql",
                tables_used=tables_used,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
            )
            
            # Try self-correction if we have retries
            if max_retries > 0:
                corrected_sql = self._self_correct(question, sql, error_msg, schema_context)
                if corrected_sql:
                    return self.generate_and_execute(question, max_retries=max_retries - 1)
            
            return None

    def _generate_sql(
        self, question: str, schema_context: str, few_shot_examples: List
    ) -> Optional[Dict]:
        """Generate SQL using OpenAI with schema context and few-shot examples.
        
        This method is public for debugging purposes.
        """
        """Generate SQL using OpenAI with schema context and few-shot examples"""
        system = (
            "You are an expert SQL planner for the Entitlements Platform.\n"
            "You receive a natural language question and relevant schema context.\n"
            "Your job is to generate ONE safe SELECT statement.\n\n"
            "Rules:\n"
            "- Only SELECT statements (no INSERT/UPDATE/DELETE/ALTER/DROP/TRUNCATE).\n"
            "- Use the provided schema context to understand table structures and relationships.\n"
            "- For simple queries (e.g., 'what is the name of user X'), use direct table queries without unnecessary JOINs.\n"
            "- Always include a LIMIT (e.g. 100 or 200) for list-style queries.\n"
            "- For single-row queries (e.g., 'what is the name of user X'), LIMIT 1 is appropriate.\n"
            "- **Application References**:\n"
            "  - If user says 'application code APP_1' or 'app code APP_1': use WHERE a.code = 'APP_1'\n"
            "  - If user says 'application id 301' or 'application ID 301' or just 'application 301' (numeric): use WHERE a.id = 301 or WHERE pr.application_id = 301\n"
            "  - For policy_rule queries with application ID, you can filter directly: WHERE pr.application_id = 301\n"
            "- Prefer using codes like 'APP_1', 'DEPT_1' etc. when referring to apps/departments by code.\n"
            "- Use proper JOINs based on foreign key relationships shown in the schema.\n"
            "- Table names use schema.table format (e.g., identity.user_account, catalog.application, entitlement.policy_rule).\n"
            "- Column names should match exactly as shown in the schema context.\n"
            "- For policy-related queries:\n"
            "  - If user mentions application CODE: join entitlement.policy_rule with catalog.application, then filter by application.code\n"
            "  - If user mentions application ID: you can filter directly on pr.application_id = <id> without joining, or join if you need application details\n"
            "- For queries asking about 'roles that have access to applications' or 'applications and roles':\n"
            "  - Join: catalog.application → entitlement.policy_rule (via application_id)\n"
            "  - Join: entitlement.policy_rule → entitlement.policy_set (via policy_set_id)\n"
            "  - Join: entitlement.policy_set → entitlement.policy_scope (via policy_set_id)\n"
            "  - Join: entitlement.policy_scope → identity.functional_role (via role_id)\n"
            "  - Filter: WHERE policy_scope.role_id IS NOT NULL AND policy_rule.grant_type = 'ALLOW'\n"
            "  - Use DISTINCT to avoid duplicates\n"
            "- Respond ONLY with a compact JSON object with keys: mode, sql, reasoning.\n"
            "- Example for simple query: {\"mode\":\"sql\",\"sql\":\"SELECT first_name, last_name FROM identity.user_account WHERE username = 'user00001' LIMIT 1;\",\"reasoning\":\"Querying user table for specific username\"}\n"
            "- Example for policy query by code: {\"mode\":\"sql\",\"sql\":\"SELECT pr.id, pr.grant_type, pr.priority, pr.condition_logic FROM entitlement.policy_rule pr JOIN catalog.application a ON a.id = pr.application_id WHERE a.code = 'APP_1' LIMIT 200;\",\"reasoning\":\"Querying policy rules for application APP_1\"}\n"
            "- Example for policy query by ID: {\"mode\":\"sql\",\"sql\":\"SELECT pr.id, pr.policy_set_id, pr.application_id, pr.grant_type, pr.priority, pr.condition_logic FROM entitlement.policy_rule pr WHERE pr.application_id = 301 LIMIT 200;\",\"reasoning\":\"Querying policy rules for application ID 301\"}\n"
        )
        
        # Build few-shot examples section
        examples_text = ""
        if few_shot_examples:
            examples_text = "\n## Example Queries (for reference):\n\n"
            for i, ex in enumerate(few_shot_examples, 1):
                examples_text += f"Example {i}:\n"
                examples_text += f"Question: {ex.question}\n"
                examples_text += f"SQL: {ex.sql}\n\n"
        
        user_content = {
            "question": question,
            "schema_context": schema_context[:8000],  # Limit context size
            "examples": examples_text,
        }
        
        client = _client()
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_content, indent=2)},
            ],
            temperature=0.2,
        )
        
        # Track token usage and cost
        usage = extract_usage_from_response(resp.usage, model=settings.openai_model)
        if usage:
            log_token_usage(usage, context="sql_generation")
        
        content = (resp.choices[0].message.content or "").strip()
        logger.info(f"Enhanced SQL generation raw LLM content: {content[:500]}...")
        
        # Parse JSON response
        try:
            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            plan = json.loads(content)
            if not isinstance(plan, dict):
                logger.warning(f"Enhanced SQL: Plan is not a dict: {type(plan)}, content: {content[:200]}")
                return None
            
            mode = plan.get("mode")
            sql = plan.get("sql")
            if not sql or not isinstance(sql, str):
                logger.warning(
                    f"Enhanced SQL: Missing or invalid SQL in plan. "
                    f"Mode: {mode}, SQL type: {type(sql)}, Plan keys: {list(plan.keys())}, "
                    f"Full plan: {plan}"
                )
                return None
            
            logger.info(f"Enhanced SQL: Generated SQL: {sql}")
            
            # Basic safety checks
            low = sql.lower().strip()
            if not low.startswith("select"):
                logger.warning("SQL does not start with SELECT")
                return None
            
            banned = ["insert", "update", "delete", "drop", "alter", "truncate", "create", "grant"]
            if any(b in low for b in banned):
                logger.warning(f"Banned keyword in SQL: {sql}")
                return None
            
            # Ensure LIMIT (but not for single-row queries)
            # Check for LIMIT more carefully using regex (handles newlines, case-insensitive)
            has_limit = re.search(r'\blimit\s+\d+', low, re.IGNORECASE)
            if not has_limit:
                # For questions asking for specific single values, use LIMIT 1
                if any(word in question.lower() for word in ["what is", "who is", "which is", "the name", "the email"]):
                    sql = sql.rstrip(" ;") + " LIMIT 1"
                    logger.info("Enhanced SQL: Added LIMIT 1 (was missing, single-row query)")
                else:
                    sql = sql.rstrip(" ;") + " LIMIT 200"
                    logger.info("Enhanced SQL: Added LIMIT 200 (was missing)")
            else:
                logger.info("Enhanced SQL: SQL already has LIMIT clause, not adding duplicate")
            
            logger.info(f"Enhanced SQL: Final SQL after processing: {sql}")
            return {
                "mode": mode,
                "sql": sql,
                "reasoning": plan.get("reasoning", ""),
            }
        except json.JSONDecodeError as e:
            logger.warning(f"Enhanced SQL: Failed to parse JSON from LLM: {e}, content: {content[:500]}")
            return None

    def _validate_sql(self, sql: str) -> Dict:
        """Validate SQL syntax and safety"""
        # Check for multiple statements (ignore semicolons inside strings)
        sql_clean = re.sub(r"';", "", sql)  # Remove semicolons inside strings
        semicolon_count = sql_clean.count(";")
        
        if semicolon_count > 1:
            return {"valid": False, "error": "Multiple statements not allowed"}
        
        # Remove trailing semicolon for EXPLAIN
        sql_for_explain = sql.rstrip().rstrip(';')
        
        # Try EXPLAIN to validate syntax
        try:
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"EXPLAIN {sql_for_explain}")
                    cur.fetchall()
            return {"valid": True}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def _self_correct(
        self, question: str, original_sql: str, error: str, schema_context: str
    ) -> Optional[str]:
        """Attempt to self-correct SQL based on error message"""
        logger.info(f"Attempting self-correction for SQL error: {error}")
        
        system = (
            "You are a SQL error corrector. You receive a SQL query that failed, "
            "the error message, and the original question. Your job is to generate "
            "a corrected SQL query.\n\n"
            "Rules:\n"
            "- Only SELECT statements.\n"
            "- Fix the specific error mentioned.\n"
            "- Use the schema context to ensure correct table/column names.\n"
            "- Respond with ONLY the corrected SQL query, no explanation.\n"
        )
        
        user_content = {
            "original_question": question,
            "failed_sql": original_sql,
            "error_message": error,
            "schema_context": schema_context[:4000],
        }
        
        client = _client()
        resp = client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_content, indent=2)},
            ],
            temperature=0.1,
        )
        
        # Track token usage and cost
        usage = extract_usage_from_response(resp.usage, model=settings.openai_model)
        if usage:
            log_token_usage(usage, context="sql_self_correction")
        
        corrected = (resp.choices[0].message.content or "").strip()
        # Remove markdown code blocks if present
        corrected = re.sub(r"```sql\n?", "", corrected)
        corrected = re.sub(r"```\n?", "", corrected)
        corrected = corrected.strip()
        
        if corrected and corrected.lower().startswith("select"):
            logger.info(f"Self-correction generated new SQL")
            return corrected
        
        return None

    def _execute_sql(self, sql: str) -> tuple:
        """Execute SQL and return rows and count"""
        # Final safeguard: disallow multiple statements
        # Count semicolons, but ignore those inside strings
        sql_clean = re.sub(r"';", "", sql)  # Remove semicolons inside strings
        semicolon_count = sql_clean.count(";")
        
        if semicolon_count > 1:
            raise ValueError("Multiple statements not allowed")
        
        # Remove trailing semicolon if present (single statement terminator is OK)
        sql = sql.rstrip().rstrip(';')
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()
                row_count = len(rows)
        
        return rows, row_count

    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL (simple heuristic)"""
        # Look for FROM and JOIN clauses
        tables = []
        patterns = [
            r"FROM\s+(\w+\.\w+|\w+)",
            r"JOIN\s+(\w+\.\w+|\w+)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)
        return list(set(tables))

