"""
Query Bank for Option 1

Stores successful query patterns for few-shot learning and continuous improvement.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger("entitlements-chat.query_bank")


@dataclass
class QueryExample:
    """A successful query example"""
    question: str
    sql: str
    intent: str
    tables_used: List[str]
    success: bool = True
    error_message: Optional[str] = None
    created_at: str = ""
    execution_time_ms: Optional[float] = None
    row_count: Optional[int] = None


class QueryBank:
    """Manages a bank of successful query examples"""

    def __init__(self, bank_path: Optional[Path] = None):
        if bank_path is None:
            bank_path = Path(__file__).parent / "query_bank.json"
        self.bank_path = bank_path
        self.examples: List[QueryExample] = []
        self._load()

    def _load(self):
        """Load query bank from file"""
        if self.bank_path.exists():
            try:
                data = json.loads(self.bank_path.read_text(encoding="utf-8"))
                self.examples = [
                    QueryExample(**ex) for ex in data.get("examples", [])
                ]
                logger.info(f"Loaded {len(self.examples)} query examples from bank")
            except Exception as e:
                logger.warning(f"Failed to load query bank: {e}")
                self.examples = []
        else:
            self.examples = []

    def _save(self):
        """Save query bank to file"""
        try:
            data = {
                "examples": [asdict(ex) for ex in self.examples],
                "updated_at": datetime.now().isoformat(),
            }
            self.bank_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save query bank: {e}")

    def add_example(
        self,
        question: str,
        sql: str,
        intent: str,
        tables_used: List[str],
        success: bool = True,
        error_message: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        row_count: Optional[int] = None,
    ):
        """Add a query example to the bank"""
        example = QueryExample(
            question=question,
            sql=sql,
            intent=intent,
            tables_used=tables_used,
            success=success,
            error_message=error_message,
            created_at=datetime.now().isoformat(),
            execution_time_ms=execution_time_ms,
            row_count=row_count,
        )
        self.examples.append(example)
        self._save()
        logger.info(f"Added query example to bank: {intent}")

    def get_few_shot_examples(
        self,
        question: str,
        intent: Optional[str] = None,
        max_examples: int = 3,
    ) -> List[QueryExample]:
        """
        Get similar query examples for few-shot learning.
        Returns examples that match the intent or are similar to the question.
        """
        # Filter by intent if provided
        candidates = self.examples
        if intent:
            candidates = [ex for ex in candidates if ex.intent == intent and ex.success]
        
        # Filter to successful examples only
        candidates = [ex for ex in candidates if ex.success]
        
        # Simple similarity: check for common keywords
        # In production, could use embeddings for better similarity
        question_lower = question.lower()
        scored = []
        for ex in candidates:
            score = 0
            ex_lower = ex.question.lower()
            # Check for common words
            question_words = set(question_lower.split())
            ex_words = set(ex_lower.split())
            common = question_words & ex_words
            score = len(common)
            scored.append((score, ex))
        
        # Sort by score and return top N
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:max_examples]]

    def get_examples_for_tables(self, tables: List[str]) -> List[QueryExample]:
        """Get examples that use the specified tables"""
        table_set = set(t.lower() for t in tables)
        return [
            ex for ex in self.examples
            if ex.success and table_set.intersection(set(t.lower() for t in ex.tables_used))
        ]

    def get_statistics(self) -> Dict:
        """Get statistics about the query bank"""
        total = len(self.examples)
        successful = len([ex for ex in self.examples if ex.success])
        failed = total - successful
        
        intents = {}
        for ex in self.examples:
            intents[ex.intent] = intents.get(ex.intent, 0) + 1
        
        return {
            "total_examples": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "intents": intents,
        }

