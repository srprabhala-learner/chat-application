"""
Enhanced Schema Retrieval for Option 1

Uses RAG to retrieve relevant schema information based on user questions.
This is more intelligent than providing the entire schema - it retrieves
only the relevant tables, columns, and relationships.
"""

import logging
from typing import List, Dict, Optional

from app.retrieval import retrieve_context

logger = logging.getLogger("entitlements-chat.schema_retrieval")


class SchemaRetriever:
    """Retrieves relevant schema information using RAG"""

    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def retrieve_relevant_schema(self, question: str) -> str:
        """
        Retrieve relevant schema chunks based on the question.
        Returns a formatted schema context for SQL generation.
        """
        logger.info(f"Schema retrieval: Searching for schema context for question: {question}")
        
        question_lower = question.lower()
        is_architecture_question = any(word in question_lower for word in [
            "architecture", "entities", "business flow", "how does", "explain", 
            "overview", "structure", "relationship", "domain", "component"
        ])
        
        # For architecture questions, get more chunks and prioritize architecture/overview chunks
        top_k_multiplier = 3 if is_architecture_question else 2
        
        # Use RAG to find relevant schema chunks
        hits = retrieve_context(question, top_k=self.top_k * top_k_multiplier)
        logger.info(f"Schema retrieval: Found {len(hits)} total hits")
        
        # Filter for schema chunks
        schema_hits = [
            h for h in hits
            if h.get("source_path", "").endswith("schema.sql") or
               h.get("chunk_id", "").startswith("schema:") or
               h.get("source_path", "").endswith("BUSINESS_ARCHITECTURE.md") or
               h.get("source_path", "").endswith("README.md")
        ]
        logger.info(f"Schema retrieval: Found {len(schema_hits)} schema/architecture-specific hits")
        
        # For architecture questions, prioritize architecture overview chunks
        if is_architecture_question:
            arch_hits = [h for h in schema_hits if "architecture" in h.get("chunk_id", "").lower() or 
                        "BUSINESS_ARCHITECTURE" in h.get("source_path", "")]
            if arch_hits:
                schema_hits = arch_hits + [h for h in schema_hits if h not in arch_hits]
                logger.info(f"Schema retrieval: Prioritized {len(arch_hits)} architecture chunks")
        
        # If we have schema hits, use them; otherwise use all hits
        relevant_hits = schema_hits[:self.top_k * 2] if schema_hits else hits[:self.top_k]
        
        if not relevant_hits:
            logger.warning(f"Schema retrieval: No schema chunks found for question: {question}")
            return "# No relevant schema information found.\n"
        
        logger.info(f"Schema retrieval: Using {len(relevant_hits)} relevant hits")
        
        # Combine into a single context
        context_parts = []
        seen_chunks = set()
        
        for hit in relevant_hits:
            chunk_id = hit.get("chunk_id", "")
            if chunk_id in seen_chunks:
                continue
            seen_chunks.add(chunk_id)
            
            content = hit.get("content", "")
            source = hit.get("source_path", "")
            score = hit.get("score", 0.0)
            
            context_parts.append(f"## Context (relevance: {score:.3f})\n")
            context_parts.append(f"Source: {source}\n")
            context_parts.append(content)
            context_parts.append("\n---\n")
        
        return "\n".join(context_parts)

    def get_table_schema(self, schema_name: str, table_name: str) -> Optional[str]:
        """Get specific table schema by name"""
        query = f"{schema_name}.{table_name} table schema columns"
        hits = retrieve_context(query, top_k=3)
        
        for hit in hits:
            chunk_id = hit.get("chunk_id", "")
            if f"schema:table:{schema_name}.{table_name}" in chunk_id:
                return hit.get("content", "")
        
        return None

    def find_related_tables(self, table_name: str) -> List[Dict]:
        """Find tables related to the given table via foreign keys"""
        query = f"relationships foreign keys {table_name}"
        hits = retrieve_context(query, top_k=5)
        
        related = []
        for hit in hits:
            content = hit.get("content", "")
            # Extract table names from content
            # This is a simple heuristic - could be improved
            if table_name.lower() in content.lower():
                related.append({
                    "chunk_id": hit.get("chunk_id"),
                    "content": content,
                    "score": hit.get("score", 0.0),
                })
        
        return related

