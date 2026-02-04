from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse
from app.ingest import run_ingestion
from app.chat_handlers import get_handler

app = FastAPI(title="Entitlements Chat (RAG)", version="0.1.0")

logger = logging.getLogger("entitlements-chat")
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize handler based on mode
_handler = None


def get_chat_handler():
    """Get or create the chat handler based on current mode"""
    global _handler
    current_mode = settings.mode_of_implementation
    if _handler is None or not hasattr(_handler, '_mode') or _handler._mode != current_mode:
        _handler = get_handler(current_mode)
        _handler._mode = current_mode  # Store mode for change detection
        logger.info(f"Initialized chat handler for mode: {current_mode}")
    return _handler


@app.get("/health")
def health():
    return {
        "ok": True,
        "mode": settings.mode_of_implementation,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Handle chat requests using the configured implementation mode"""
    handler = get_chat_handler()
    return handler.handle(req)


@app.post("/api/ingest")
def ingest():
    # Assumes entitlements-app is a sibling folder to chat-app-entitlements
    entitlements_root = Path(__file__).resolve().parents[3] / "entitlements-app"
    result = run_ingestion(entitlements_root=entitlements_root)
    return {"ok": True, "result": result, "entitlements_root": str(entitlements_root)}


@app.post("/api/debug/schema-retrieval")
def debug_schema_retrieval(req: dict):
    """Debug endpoint to test schema retrieval"""
    from app.schema_retrieval import SchemaRetriever
    question = req.get("question", "")
    retriever = SchemaRetriever()
    schema_context = retriever.retrieve_relevant_schema(question)
    return {
        "question": question,
        "schema_context_length": len(schema_context),
        "schema_context_preview": schema_context[:1000],
        "full_schema_context": schema_context,
    }


@app.post("/api/debug/sql-generation")
def debug_sql_generation(req: dict):
    """Debug endpoint to test SQL generation"""
    from app.sql_generate_v2 import EnhancedSQLGenerator
    question = req.get("question", "")
    generator = EnhancedSQLGenerator()
    
    # Get schema context
    schema_context = generator.schema_retriever.retrieve_relevant_schema(question)
    
    # Get few-shot examples
    few_shot_examples = generator.query_bank.get_few_shot_examples(question, max_examples=3)
    
    # Try to generate SQL
    sql_result = generator._generate_sql(question, schema_context, few_shot_examples)
    
    return {
        "question": question,
        "schema_context_length": len(schema_context),
        "schema_context_preview": schema_context[:1000],
        "few_shot_examples_count": len(few_shot_examples),
        "sql_result": sql_result,
        "success": sql_result is not None,
    }


