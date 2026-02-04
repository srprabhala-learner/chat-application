"""
Schema Knowledge Graph Builder for Option 1

Builds and stores a knowledge graph of database schema relationships
for efficient retrieval and query generation.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from app.schema_parser import SchemaParser, SchemaGraph
from app.rag_store import upsert_chunks
from app.embeddings import embed_texts

logger = logging.getLogger("entitlements-chat.schema_graph")


class SchemaGraphBuilder:
    """Builds and stores schema knowledge graph in vector DB"""

    def __init__(self):
        self.parser = SchemaParser()

    def build_and_store(self, ddl_path: Path, entitlements_root: Path) -> dict:
        """
        Parse DDL, build knowledge graph, and store in vector DB.
        Returns summary of what was stored.
        """
        logger.info(f"Building schema graph from: {ddl_path}")
        
        # Parse DDL
        graph = self.parser.parse_ddl_file(ddl_path)
        
        # Generate chunks for vector storage
        chunks = self._generate_schema_chunks(graph, ddl_path, entitlements_root)
        
        # Embed and store
        contents = [c["content"] for c in chunks]
        embeddings = embed_texts(contents)
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        
        upserted = upsert_chunks(chunks)
        
        logger.info(f"Stored {upserted} schema chunks in vector DB")
        
        return {
            "tables": len(graph.tables),
            "relationships": len(graph.relationships),
            "chunks": len(chunks),
            "upserted": upserted,
        }

    def _generate_schema_chunks(
        self, graph: SchemaGraph, ddl_path: Path, entitlements_root: Path
    ) -> List[dict]:
        """Generate text chunks from schema graph for vector storage"""
        chunks = []
        source_path = str(ddl_path.relative_to(entitlements_root))
        
        # Chunk 1: Overall schema summary
        summary = self.parser.get_schema_summary()
        chunks.append({
            "chunk_id": f"schema:summary",
            "source_path": source_path,
            "content": summary,
        })
        
        # Chunk 2: Table-level chunks (one per table)
        for table_key, table in graph.tables.items():
            table_content = self._format_table_chunk(table, graph)
            chunks.append({
                "chunk_id": f"schema:table:{table_key}",
                "source_path": source_path,
                "content": table_content,
            })
        
        # Chunk 3: Relationship chunks (grouped by from-table)
        rel_by_table: Dict[str, List] = {}
        for rel in graph.relationships:
            from_key = f"{rel.from_schema}.{rel.from_table}"
            if from_key not in rel_by_table:
                rel_by_table[from_key] = []
            rel_by_table[from_key].append(rel)
        
        for table_key, rels in rel_by_table.items():
            rel_content = self._format_relationships_chunk(table_key, rels, graph)
            chunks.append({
                "chunk_id": f"schema:relationships:{table_key}",
                "source_path": source_path,
                "content": rel_content,
            })
        
        # Chunk 4: Architecture overview (synthesized from schema)
        arch_overview = self._generate_architecture_overview(graph)
        chunks.append({
            "chunk_id": f"schema:architecture",
            "source_path": source_path,
            "content": arch_overview,
        })
        
        # Chunk 5: JSON representation (for programmatic access)
        json_repr = json.dumps(self.parser.to_json(), indent=2)
        chunks.append({
            "chunk_id": f"schema:json",
            "source_path": source_path,
            "content": f"# Schema JSON Representation\n\n```json\n{json_repr}\n```",
        })
        
        return chunks

    def _generate_architecture_overview(self, graph: SchemaGraph) -> str:
        """Generate a high-level architecture overview from the schema graph"""
        lines = [
            "# Entitlements Platform - Architecture Overview",
            "",
            "This document synthesizes the database schema to explain the high-level business architecture.",
            "",
        ]
        
        # Group tables by schema
        by_schema: Dict[str, List] = {}
        for table_key, table in graph.tables.items():
            schema = table.schema
            if schema not in by_schema:
                by_schema[schema] = []
            by_schema[schema].append(table)
        
        # Describe each domain
        schema_descriptions = {
            "core": "Core Organization Structure - Tenants, regions, countries, organizational units",
            "identity": "Identity & Access - Users, roles, groups, assignments",
            "catalog": "Application Catalog - Applications, modules, features, availability",
            "entitlement": "Entitlements & Policies - Policies, rules, permissions, exceptions",
            "audit": "Audit & Logging - Change logs, snapshots, evaluation logs",
            "analytics": "Analytics & Reporting - Usage summaries, health indicators",
        }
        
        lines.append("## Domain Overview")
        lines.append("")
        for schema in sorted(by_schema.keys()):
            desc = schema_descriptions.get(schema, "Domain-specific tables")
            tables = by_schema[schema]
            lines.append(f"### {schema.upper()} Schema ({len(tables)} tables)")
            lines.append(f"{desc}")
            lines.append("")
            lines.append("**Key Tables:**")
            for table in sorted(tables, key=lambda t: t.name)[:10]:  # Top 10 per schema
                lines.append(f"- `{schema}.{table.name}`")
            if len(tables) > 10:
                lines.append(f"- ... and {len(tables) - 10} more tables")
            lines.append("")
        
        # Describe key relationships
        lines.append("## Key Relationships")
        lines.append("")
        lines.append("### Organization Hierarchy")
        lines.append("- Tenant → Regions → Countries")
        lines.append("- Tenant → Organization Units (hierarchical via parent_id)")
        lines.append("- Organization Units → Regions")
        lines.append("")
        
        lines.append("### Identity Relationships")
        lines.append("- User → Department (via primary_org_unit_id)")
        lines.append("- User → Roles (via user_role_assignment)")
        lines.append("- User → Groups (via group_membership)")
        lines.append("")
        
        lines.append("### Application Relationships")
        lines.append("- Application → Modules → Features")
        lines.append("- Application → Instances (deployment locations)")
        lines.append("- Application → Availability Rules (department/region access)")
        lines.append("")
        
        lines.append("### Entitlement Relationships")
        lines.append("- Policy Set → Policy Scope (who/where)")
        lines.append("- Policy Set → Policy Rules (what)")
        lines.append("- Policy Rule → Application")
        lines.append("- User → Entitlements (final grants)")
        lines.append("")
        
        # Count relationships by type
        fk_relationships = {}
        for rel in graph.relationships:
            to_key = f"{rel.to_schema}.{rel.to_table}"
            if to_key not in fk_relationships:
                fk_relationships[to_key] = []
            fk_relationships[to_key].append(f"{rel.from_schema}.{rel.from_table}.{rel.from_column}")
        
        lines.append("## Entity Relationship Summary")
        lines.append("")
        lines.append(f"Total tables: {len(graph.tables)}")
        lines.append(f"Total relationships: {len(graph.relationships)}")
        lines.append("")
        
        return "\n".join(lines)

    def _format_table_chunk(self, table, graph: SchemaGraph) -> str:
        """Format a table as a text chunk"""
        lines = [
            f"# Table: {table.schema}.{table.name}",
            "",
        ]
        
        if table.primary_key:
            lines.append(f"**Primary Key**: {', '.join(table.primary_key)}")
            lines.append("")
        
        lines.append("## Columns")
        for col_name, col in sorted(table.columns.items()):
            markers = []
            if col.is_primary_key:
                markers.append("PRIMARY KEY")
            if col.is_foreign_key:
                markers.append(f"FOREIGN KEY → {col.foreign_table}.{col.foreign_column}")
            if not col.nullable:
                markers.append("NOT NULL")
            
            marker_str = f" [{', '.join(markers)}]" if markers else ""
            lines.append(f"- `{col.name}`: {col.data_type}{marker_str}")
        
        # Add outgoing relationships
        outgoing = [
            rel for rel in graph.relationships
            if rel.from_schema == table.schema and rel.from_table == table.name
        ]
        if outgoing:
            lines.append("")
            lines.append("## Relationships (Outgoing)")
            for rel in outgoing:
                lines.append(
                    f"- `{rel.from_column}` → `{rel.to_schema}.{rel.to_table}.{rel.to_column}`"
                )
        
        # Add incoming relationships
        incoming = [
            rel for rel in graph.relationships
            if rel.to_schema == table.schema and rel.to_table == table.name
        ]
        if incoming:
            lines.append("")
            lines.append("## Relationships (Incoming)")
            for rel in incoming:
                lines.append(
                    f"- `{rel.from_schema}.{rel.from_table}.{rel.from_column}` → `{rel.to_column}`"
                )
        
        return "\n".join(lines)

    def _format_relationships_chunk(self, table_key: str, rels: List, graph: SchemaGraph) -> str:
        """Format relationships for a table as a text chunk"""
        lines = [
            f"# Relationships for {table_key}",
            "",
            "This table has the following foreign key relationships:",
            "",
        ]
        
        for rel in rels:
            lines.append(
                f"- `{rel.from_column}` references `{rel.to_schema}.{rel.to_table}.{rel.to_column}`"
            )
            lines.append(
                f"  - Type: {rel.relationship_type}"
            )
            lines.append("")
        
        return "\n".join(lines)

    def load_schema_json(self, ddl_path: Path) -> Optional[dict]:
        """Load parsed schema as JSON (for programmatic access)"""
        graph = self.parser.parse_ddl_file(ddl_path)
        return self.parser.to_json()

