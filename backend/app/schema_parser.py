"""
Schema Parser for Option 1: Enhanced RAG + Structured Schema Understanding

Parses PostgreSQL DDL files to extract:
- Tables, columns, data types
- Primary keys, foreign keys
- Constraints, indexes
- Relationships (one-to-many, many-to-many)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set
from pathlib import Path

logger = logging.getLogger("entitlements-chat.schema_parser")


@dataclass
class Column:
    """Represents a database column"""
    name: str
    data_type: str
    nullable: bool = True
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None
    foreign_column: Optional[str] = None
    description: Optional[str] = None


@dataclass
class Table:
    """Represents a database table"""
    schema: str
    name: str
    columns: Dict[str, Column] = field(default_factory=dict)
    primary_key: Optional[List[str]] = None
    indexes: List[str] = field(default_factory=list)
    description: Optional[str] = None


@dataclass
class Relationship:
    """Represents a foreign key relationship"""
    from_schema: str
    from_table: str
    from_column: str
    to_schema: str
    to_table: str
    to_column: str
    relationship_type: str = "many-to-one"  # many-to-one, one-to-many, many-to-many


@dataclass
class SchemaGraph:
    """Complete schema knowledge graph"""
    tables: Dict[str, Table] = field(default_factory=dict)  # key: "schema.table"
    relationships: List[Relationship] = field(default_factory=list)
    schemas: Set[str] = field(default_factory=set)


class SchemaParser:
    """Parses PostgreSQL DDL to build a structured schema graph"""

    def __init__(self):
        self.current_schema = "public"
        self.graph = SchemaGraph()

    def parse_ddl_file(self, ddl_path: Path) -> SchemaGraph:
        """Parse a DDL file and return a SchemaGraph"""
        logger.info(f"Parsing DDL file: {ddl_path}")
        content = ddl_path.read_text(encoding="utf-8", errors="ignore")
        return self.parse_ddl_content(content)

    def parse_ddl_content(self, ddl_content: str) -> SchemaGraph:
        """Parse DDL content string"""
        # Reset state
        self.graph = SchemaGraph()
        self.current_schema = "public"

        # Normalize: remove comments, collapse whitespace
        content = self._normalize_ddl(ddl_content)

        # Extract schema declarations
        self._extract_schemas(content)

        # Extract table definitions
        self._extract_tables(content)

        # Extract relationships (foreign keys)
        self._extract_relationships(content)

        logger.info(f"Parsed schema: {len(self.graph.tables)} tables, {len(self.graph.relationships)} relationships")
        return self.graph

    def _normalize_ddl(self, content: str) -> str:
        """Normalize DDL content for easier parsing"""
        # Remove single-line comments
        content = re.sub(r'--.*?$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Collapse multiple whitespace
        content = re.sub(r'\s+', ' ', content)
        return content

    def _extract_schemas(self, content: str):
        """Extract CREATE SCHEMA statements"""
        pattern = r'CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)'
        for match in re.finditer(pattern, content, re.IGNORECASE):
            schema = match.group(1).lower()
            self.graph.schemas.add(schema)

    def _extract_tables(self, content: str):
        """Extract CREATE TABLE statements"""
        # Pattern to match CREATE TABLE with schema
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:(\w+)\.)?(\w+)\s*\((.*?)\)'
        
        for match in re.finditer(pattern, content, re.IGNORECASE | re.DOTALL):
            schema = (match.group(1) or "public").lower()
            table_name = match.group(2).lower()
            table_body = match.group(3)
            
            self.current_schema = schema
            self.graph.schemas.add(schema)
            
            table_key = f"{schema}.{table_name}"
            table = Table(schema=schema, name=table_name)
            
            # Parse columns and constraints
            self._parse_table_body(table, table_body)
            
            self.graph.tables[table_key] = table

    def _parse_table_body(self, table: Table, body: str):
        """Parse table body to extract columns and constraints"""
        # Split by commas, but be careful with nested parentheses
        parts = self._split_table_body(body)
        
        primary_key_cols = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # PRIMARY KEY constraint
            pk_match = re.search(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
            if pk_match:
                cols = [c.strip().lower() for c in pk_match.group(1).split(',')]
                primary_key_cols = cols
                for col_name in cols:
                    if col_name in table.columns:
                        table.columns[col_name].is_primary_key = True
                table.primary_key = cols
                continue
            
            # Column definition
            col_match = re.match(r'(\w+)\s+(\w+(?:\([^)]+\))?)', part, re.IGNORECASE)
            if col_match:
                col_name = col_match.group(1).lower()
                data_type = col_match.group(2).lower()
                
                nullable = "NOT NULL" not in part.upper()
                default_match = re.search(r"DEFAULT\s+([^,\s]+)", part, re.IGNORECASE)
                default_value = default_match.group(1) if default_match else None
                
                column = Column(
                    name=col_name,
                    data_type=data_type,
                    nullable=nullable,
                    default_value=default_value
                )
                
                if col_name in primary_key_cols:
                    column.is_primary_key = True
                
                table.columns[col_name] = column

    def _split_table_body(self, body: str) -> List[str]:
        """Split table body by commas, respecting parentheses"""
        parts = []
        current = []
        depth = 0
        
        for char in body:
            if char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        if current:
            parts.append(''.join(current).strip())
        
        return parts

    def _extract_relationships(self, content: str):
        """Extract foreign key relationships"""
        # Pattern: REFERENCES schema.table(column) or REFERENCES table(column)
        pattern = r'(\w+)\s+REFERENCES\s+(?:(\w+)\.)?(\w+)\s*\((\w+)\)'
        
        current_table = None
        current_schema = "public"
        
        # Find all CREATE TABLE blocks first
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:(\w+)\.)?(\w+)\s*\('
        for match in re.finditer(table_pattern, content, re.IGNORECASE):
            current_schema = (match.group(1) or "public").lower()
            current_table = match.group(2).lower()
            
            # Find REFERENCES in this table's body
            table_start = match.end()
            # Find matching closing parenthesis
            table_end = self._find_matching_paren(content, table_start)
            table_body = content[table_start:table_end]
            
            # Extract foreign keys from this table
            for fk_match in re.finditer(pattern, table_body, re.IGNORECASE):
                from_column = fk_match.group(1).lower()
                to_schema = (fk_match.group(2) or current_schema).lower()
                to_table = fk_match.group(3).lower()
                to_column = fk_match.group(4).lower()
                
                relationship = Relationship(
                    from_schema=current_schema,
                    from_table=current_table,
                    from_column=from_column,
                    to_schema=to_schema,
                    to_table=to_table,
                    to_column=to_column,
                    relationship_type="many-to-one"
                )
                
                self.graph.relationships.append(relationship)
                
                # Mark column as foreign key
                table_key = f"{current_schema}.{current_table}"
                if table_key in self.graph.tables:
                    if from_column in self.graph.tables[table_key].columns:
                        col = self.graph.tables[table_key].columns[from_column]
                        col.is_foreign_key = True
                        col.foreign_table = f"{to_schema}.{to_table}"
                        col.foreign_column = to_column

    def _find_matching_paren(self, text: str, start_pos: int) -> int:
        """Find the matching closing parenthesis"""
        depth = 1
        pos = start_pos
        while pos < len(text) and depth > 0:
            if text[pos] == '(':
                depth += 1
            elif text[pos] == ')':
                depth -= 1
            pos += 1
        return pos

    def to_json(self) -> dict:
        """Convert schema graph to JSON representation"""
        return {
            "schemas": list(self.graph.schemas),
            "tables": {
                key: {
                    "schema": table.schema,
                    "name": table.name,
                    "columns": {
                        col_name: {
                            "name": col.name,
                            "data_type": col.data_type,
                            "nullable": col.nullable,
                            "default_value": col.default_value,
                            "is_primary_key": col.is_primary_key,
                            "is_foreign_key": col.is_foreign_key,
                            "foreign_table": col.foreign_table,
                            "foreign_column": col.foreign_column,
                        }
                        for col_name, col in table.columns.items()
                    },
                    "primary_key": table.primary_key,
                }
                for key, table in self.graph.tables.items()
            },
            "relationships": [
                {
                    "from": f"{rel.from_schema}.{rel.from_table}.{rel.from_column}",
                    "to": f"{rel.to_schema}.{rel.to_table}.{rel.to_column}",
                    "type": rel.relationship_type,
                }
                for rel in self.graph.relationships
            ],
        }

    def get_schema_summary(self) -> str:
        """Generate a human-readable schema summary for LLM context"""
        lines = ["# Database Schema Summary\n"]
        
        for schema in sorted(self.graph.schemas):
            lines.append(f"## Schema: {schema}\n")
            
            schema_tables = [
                (key, table) for key, table in self.graph.tables.items()
                if table.schema == schema
            ]
            
            for table_key, table in sorted(schema_tables):
                lines.append(f"### Table: {schema}.{table.name}")
                lines.append(f"**Primary Key**: {', '.join(table.primary_key) if table.primary_key else 'None'}\n")
                
                lines.append("**Columns:**")
                for col_name, col in sorted(table.columns.items()):
                    pk_marker = " [PK]" if col.is_primary_key else ""
                    fk_marker = f" [FK → {col.foreign_table}.{col.foreign_column}]" if col.is_foreign_key else ""
                    nullable_marker = "" if col.nullable else " [NOT NULL]"
                    lines.append(f"  - `{col.name}`: {col.data_type}{pk_marker}{fk_marker}{nullable_marker}")
                
                lines.append("")
        
        lines.append("## Relationships\n")
        for rel in self.graph.relationships:
            lines.append(
                f"- `{rel.from_schema}.{rel.from_table}.{rel.from_column}` → "
                f"`{rel.to_schema}.{rel.to_table}.{rel.to_column}` ({rel.relationship_type})"
            )
        
        return "\n".join(lines)

