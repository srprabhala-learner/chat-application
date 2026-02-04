"""
Chat Handlers for Different Implementation Options

This module provides handlers for different implementation modes:
- Option 1: Enhanced RAG + Structured Schema Understanding
- Option 2: Agentic Architecture (to be implemented)
- Option 3: Fine-Tuned Model (to be implemented)
- Option 4: Hybrid (to be implemented)
- Legacy: Current template-based approach
"""

import logging
from typing import Dict, Optional

from app.models import ChatRequest, ChatResponse, Citation
from app.retrieval import retrieve_context
from app.llm_openai import answer_with_context
from app.sql_generate_v2 import EnhancedSQLGenerator
from app.intent_router import classify_intent

logger = logging.getLogger("entitlements-chat.handlers")


class BaseChatHandler:
    """Base class for chat handlers"""
    
    def handle(self, req: ChatRequest) -> ChatResponse:
        """Handle a chat request. Must be implemented by subclasses."""
        raise NotImplementedError


class Option1Handler(BaseChatHandler):
    """
    Option 1: Enhanced RAG + Structured Schema Understanding
    
    Features:
    - RAG-based schema retrieval (only relevant tables/columns)
    - Enhanced text-to-SQL with self-correction
    - Query bank for few-shot learning
    - Automatic relationship discovery
    """
    
    def __init__(self):
        self.sql_generator = EnhancedSQLGenerator()
    
    def handle(self, req: ChatRequest) -> ChatResponse:
        """Handle chat request using Option 1 approach"""
        logger.info(f"Option 1: Processing question: {req.message}")
        
        # Classify intent (knowledge vs data)
        intent_info = classify_intent(req.message)
        logger.info(f"Option 1: Classified intent: {intent_info}")
        
        # Determine if this is an architecture/explanation question
        question_lower = req.message.lower()
        is_architecture_question = any(word in question_lower for word in [
            "architecture", "entities", "business flow", "how does", "explain", 
            "overview", "structure", "relationship", "domain", "component", "detail",
            "different entities", "high level"
        ])
        
        # Retrieve context for RAG (get more chunks for architecture questions)
        top_k = 15 if is_architecture_question else 8
        hits = retrieve_context(req.message, top_k=top_k)
        
        # For architecture questions, also try to get schema architecture chunk
        if is_architecture_question:
            arch_query = "architecture overview entities relationships business flow"
            arch_hits = retrieve_context(arch_query, top_k=5)
            # Merge and deduplicate
            seen_ids = {h.get("chunk_id") for h in hits}
            for arch_hit in arch_hits:
                if arch_hit.get("chunk_id") not in seen_ids:
                    hits.append(arch_hit)
                    seen_ids.add(arch_hit.get("chunk_id"))
            logger.info(f"Option 1: Retrieved {len(hits)} total chunks for architecture question")
        
        conversation_id = req.conversation_id or "conv-1"
        citations = [
            Citation(source_path=h["source_path"], chunk_id=h["chunk_id"])
            for h in hits
        ]
        
        # If it's a knowledge-only question, use RAG
        if intent_info["intent"] == "knowledge_only" or is_architecture_question:
            logger.info(f"Option 1: Using RAG for {'architecture' if is_architecture_question else 'knowledge'} question")
            answer = answer_with_context(req.message, hits)
            return ChatResponse(
                conversation_id=conversation_id,
                answer=answer,
                citations=citations,
            )
        
        # For data questions, try enhanced SQL generation
        logger.info("Option 1: Attempting enhanced SQL generation...")
        sql_result = self.sql_generator.generate_and_execute(req.message)
        
        if sql_result:
            logger.info(f"Option 1: SQL generation succeeded")
            logger.info(
                f"Option 1: SQL generated and executed successfully. "
                f"Tables: {sql_result.get('tables_used')}, "
                f"Rows: {sql_result.get('row_count')}"
            )
            
            rows = sql_result["rows"]
            preview = rows[:25]
            question_aug = (
                f"{req.message}\n\n"
                f"SQL_GENERATED: {sql_result['sql']}\n"
                f"SQL_REASONING: {sql_result.get('reasoning', '')}\n"
                f"SQL_TABLES_USED: {', '.join(sql_result.get('tables_used', []))}\n"
                f"SQL_ROW_COUNT: {len(rows)}\n"
                f"SQL_EXECUTION_TIME_MS: {sql_result.get('execution_time_ms', 0):.2f}\n"
                f"SQL_ROWS_PREVIEW (first {len(preview)}): {preview}\n"
            )
            answer = answer_with_context(question_aug, hits)
            return ChatResponse(
                conversation_id=conversation_id,
                answer=answer,
                citations=citations,
            )
        
        # Fallback to RAG if SQL generation fails
        logger.warning(
            f"Option 1: SQL generation failed for question: {req.message}. "
            f"Intent was: {intent_info['intent']}. Falling back to RAG."
        )
        
        # Try legacy SQL generation as a fallback
        logger.info("Option 1: Attempting legacy SQL generation as fallback...")
        try:
            from app.sql_generate import generate_sql_plan, run_sql_plan
            plan = generate_sql_plan(req.message)
            if plan and plan.get("mode") == "sql":
                logger.info(f"Option 1: Legacy SQL plan generated: {plan.get('sql')[:100]}...")
                legacy_result = run_sql_plan(plan)
                if legacy_result:
                    logger.info(f"Option 1: Legacy SQL executed successfully, rows: {legacy_result.get('row_count')}")
                    rows = legacy_result["rows"]
                    preview = rows[:25]
                    question_aug = (
                        f"{req.message}\n\n"
                        f"SQL_GENERATED (legacy): {legacy_result['sql']}\n"
                        f"SQL_ROW_COUNT: {len(rows)}\n"
                        f"SQL_ROWS_PREVIEW (first {len(preview)}): {preview}\n"
                    )
                    answer = answer_with_context(question_aug, hits)
                    return ChatResponse(
                        conversation_id=conversation_id,
                        answer=answer,
                        citations=citations,
                    )
        except Exception as e:
            logger.warning(f"Option 1: Legacy SQL fallback also failed: {e}")
        
        # Final fallback: RAG only
        answer = answer_with_context(req.message, hits)
        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            citations=citations,
        )


class LegacyHandler(BaseChatHandler):
    """
    Legacy: Current template-based approach
    
    Uses:
    - Intent classification with templates
    - Generic text-to-SQL as fallback
    - Template-based SQL execution
    """
    
    def handle(self, req: ChatRequest) -> ChatResponse:
        """Handle chat request using legacy approach"""
        logger.info(f"Legacy: Processing question: {req.message}")
        
        # Import legacy modules
        from app.intent_router import classify_intent
        from app.sql_tool import maybe_run_safe_sql, execute_template
        from app.sql_generate import generate_sql_plan, run_sql_plan
        from app.retrieval import retrieve_context
        from app.llm_openai import answer_with_context
        
        intent_info = classify_intent(req.message)
        logger.info(f"Legacy: Classified intent: {intent_info}")
        hits = retrieve_context(req.message, top_k=8)
        conversation_id = req.conversation_id or "conv-1"
        citations = [
            Citation(source_path=h["source_path"], chunk_id=h["chunk_id"])
            for h in hits
        ]
        
        # Template path for specific intents
        template_intents = {
            "users_in_dept_for_app": ("users_in_dept_for_app", lambda i: {"app_code": i.get("app_code"), "dept_code": i.get("dept_code")}),
            "users_in_dept": ("users_in_dept", lambda i: {"dept_code": i.get("dept_code")}),
            "departments_for_app": ("departments_for_app", lambda i: {"app_code": i.get("app_code")}),
            "apps_for_dept": ("apps_for_dept", lambda i: {"dept_code": i.get("dept_code")}),
            "app_metadata": ("app_metadata", lambda i: {"app_code": i.get("app_code")}),
        }
        
        if intent_info["intent"] in template_intents:
            template_name, params_builder = template_intents[intent_info["intent"]]
            params = params_builder(intent_info)
            
            if all(v for v in params.values()):
                sql_result = execute_template(template_name, params)
                if sql_result:
                    logger.info(
                        f"Legacy: Template SQL executed. Rows: {len(sql_result.get('rows', []))}"
                    )
                    rows = sql_result["rows"]
                    preview = rows[:25]
                    question_aug = (
                        f"{req.message}\n\n"
                        f"SQL_TOOL_KIND: {sql_result['kind']}\n"
                        f"SQL_PARAMS: {sql_result.get('params', {})}\n"
                        f"SQL_ROW_COUNT: {len(rows)}\n"
                        f"SQL_ROWS_PREVIEW (first {len(preview)}): {preview}\n"
                    )
                    answer = answer_with_context(question_aug, hits)
                    return ChatResponse(
                        conversation_id=conversation_id,
                        answer=answer,
                        citations=citations,
                    )
        
        # Try generic text-to-SQL
        sql_result = None
        plan = generate_sql_plan(req.message)
        if plan and plan.get("mode") == "sql":
            try:
                logger.info(f"Legacy: SQL plan generated: {plan.get('sql')[:100]}...")
                sql_result = run_sql_plan(plan)
                logger.info(f"Legacy: SQL plan executed. Rows: {sql_result.get('row_count')}")
            except Exception as exc:
                logger.exception(f"Legacy: Error executing SQL plan: {exc}")
                sql_result = None
        
        # Fallback: heuristic SQL templates
        if not sql_result:
            sql_result = maybe_run_safe_sql(req.message)
            if sql_result:
                logger.info(f"Legacy: Heuristic SQL used. Rows: {len(sql_result.get('rows', []))}")
        
        if sql_result:
            rows = sql_result["rows"]
            preview = rows[:25]
            question_aug = (
                f"{req.message}\n\n"
                f"SQL_TOOL_KIND: {sql_result['kind']}\n"
                f"SQL_PARAMS: {sql_result.get('params', {})}\n"
                f"SQL_ROW_COUNT: {len(rows)}\n"
                f"SQL_ROWS_PREVIEW (first {len(preview)}): {preview}\n"
            )
            answer = answer_with_context(question_aug, hits)
            return ChatResponse(
                conversation_id=conversation_id,
                answer=answer,
                citations=citations,
            )
        
        # Final fallback: RAG only
        answer = answer_with_context(req.message, hits)
        return ChatResponse(
            conversation_id=conversation_id,
            answer=answer,
            citations=citations,
        )


# Placeholder handlers for future options
class Option2Handler(BaseChatHandler):
    """Option 2: Agentic Architecture (to be implemented)"""
    def handle(self, req: ChatRequest) -> ChatResponse:
        raise NotImplementedError("Option 2 not yet implemented")


class Option3Handler(BaseChatHandler):
    """Option 3: Fine-Tuned Model (to be implemented)"""
    def handle(self, req: ChatRequest) -> ChatResponse:
        raise NotImplementedError("Option 3 not yet implemented")


class Option4Handler(BaseChatHandler):
    """Option 4: Hybrid (to be implemented)"""
    def handle(self, req: ChatRequest) -> ChatResponse:
        raise NotImplementedError("Option 4 not yet implemented")


def get_handler(mode: str) -> BaseChatHandler:
    """Get the appropriate handler based on mode"""
    mode_lower = mode.lower()
    
    if mode_lower == "option1":
        return Option1Handler()
    elif mode_lower == "option2":
        return Option2Handler()
    elif mode_lower == "option3":
        return Option3Handler()
    elif mode_lower == "option4":
        return Option4Handler()
    else:
        # Default to legacy
        return LegacyHandler()

