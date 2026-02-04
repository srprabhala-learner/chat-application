# Knowledge Graph: Concept and Implementation

## What is a Knowledge Graph?

A **Knowledge Graph** is a structured representation of information that models entities (nodes) and their relationships (edges) in a graph format. Think of it as a network where:

- **Nodes** represent entities (e.g., tables, columns, concepts)
- **Edges** represent relationships between entities (e.g., foreign keys, dependencies, associations)
- **Properties** describe attributes of entities and relationships

### Key Characteristics

1. **Structured Relationships**: Explicitly models how entities connect to each other
2. **Semantic Understanding**: Captures meaning and context, not just raw data
3. **Queryable**: Can be traversed to find paths between entities
4. **Context-Aware**: Understands relationships in context (e.g., "User belongs to Department")

### Example

In a database schema knowledge graph:
- **Node**: `identity.user_account` (table)
- **Node**: `core.organization_unit` (table)
- **Edge**: `user_account.primary_org_unit_id → organization_unit.id` (foreign key relationship)
- **Meaning**: "Users belong to organizational units (departments)"

## Knowledge Graph in This Codebase

In the entitlements chat application, the knowledge graph represents the **database schema structure** - tables, columns, and their relationships - extracted from PostgreSQL DDL files.

---

## Structure of the Knowledge Graph

The knowledge graph is built using Python dataclasses and has the following structure:

### 1. Core Data Structures

#### `SchemaGraph` (Top-Level Container)

```python
@dataclass
class SchemaGraph:
    """Complete schema knowledge graph"""
    tables: Dict[str, Table]           # key: "schema.table"
    relationships: List[Relationship]  # All foreign key relationships
    schemas: Set[str]                  # All schema names
```

**Structure:**
- `tables`: Dictionary mapping `"schema.table"` → `Table` object
- `relationships`: List of all foreign key relationships
- `schemas`: Set of all schema names (core, identity, catalog, etc.)

#### `Table` (Node/Entity)

```python
@dataclass
class Table:
    """Represents a database table"""
    schema: str                        # e.g., "identity", "catalog"
    name: str                          # e.g., "user_account"
    columns: Dict[str, Column]         # Column name → Column object
    primary_key: Optional[List[str]]   # List of primary key column names
    indexes: List[str]                 # Index names
    description: Optional[str]         # Optional description
```

**Example:**
```python
Table(
    schema="identity",
    name="user_account",
    columns={
        "id": Column(name="id", data_type="bigserial", is_primary_key=True),
        "username": Column(name="username", data_type="varchar", nullable=False),
        "primary_org_unit_id": Column(
            name="primary_org_unit_id",
            data_type="bigint",
            is_foreign_key=True,
            foreign_table="core.organization_unit",
            foreign_column="id"
        )
    },
    primary_key=["id"]
)
```

#### `Column` (Property of Table)

```python
@dataclass
class Column:
    """Represents a database column"""
    name: str                          # Column name
    data_type: str                     # e.g., "bigint", "varchar(255)"
    nullable: bool = True              # Can be NULL?
    default_value: Optional[str] = None
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_table: Optional[str] = None      # e.g., "core.organization_unit"
    foreign_column: Optional[str] = None     # e.g., "id"
    description: Optional[str] = None
```

#### `Relationship` (Edge)

```python
@dataclass
class Relationship:
    """Represents a foreign key relationship"""
    from_schema: str                   # Source schema
    from_table: str                    # Source table
    from_column: str                   # Source column (foreign key)
    to_schema: str                     # Target schema
    to_table: str                      # Target table
    to_column: str                     # Target column (primary key)
    relationship_type: str = "many-to-one"  # Relationship cardinality
```

**Example:**
```python
Relationship(
    from_schema="identity",
    from_table="user_account",
    from_column="primary_org_unit_id",
    to_schema="core",
    to_table="organization_unit",
    to_column="id",
    relationship_type="many-to-one"
)
```

**Meaning**: "Many users can belong to one organizational unit"

---

## How the Knowledge Graph is Built

### Step 1: Parse DDL File

The `SchemaParser` reads a PostgreSQL DDL file (`schema.sql`) and extracts:

1. **Schemas**: `CREATE SCHEMA` statements
2. **Tables**: `CREATE TABLE` statements
3. **Columns**: Column definitions within tables
4. **Relationships**: `REFERENCES` clauses (foreign keys)

### Step 2: Build Graph Structure

```python
graph = SchemaGraph()
# Parse DDL
graph = parser.parse_ddl_file(ddl_path)

# Result:
# - graph.tables: {"identity.user_account": Table(...), ...}
# - graph.relationships: [Relationship(...), ...]
# - graph.schemas: {"core", "identity", "catalog", ...}
```

### Step 3: Generate Chunks for Vector Storage

The graph is converted into text chunks for RAG (Retrieval Augmented Generation):

1. **Schema Summary**: Overall schema overview
2. **Table Chunks**: One chunk per table with columns and relationships
3. **Relationship Chunks**: Grouped by source table
4. **Architecture Overview**: High-level business architecture synthesized from schema
5. **JSON Representation**: Complete graph in JSON format

### Step 4: Store in Vector Database

Each chunk is:
- **Embedded** using sentence transformers (384-dimensional vectors)
- **Stored** in PostgreSQL with `pgvector` extension
- **Indexed** for semantic search

---

## JSON Structure Example

When converted to JSON (`parser.to_json()`), the structure looks like:

```json
{
  "schemas": ["core", "identity", "catalog", "entitlement", "audit", "analytics"],
  "tables": {
    "identity.user_account": {
      "schema": "identity",
      "name": "user_account",
      "columns": {
        "id": {
          "name": "id",
          "data_type": "bigserial",
          "nullable": false,
          "is_primary_key": true,
          "is_foreign_key": false
        },
        "primary_org_unit_id": {
          "name": "primary_org_unit_id",
          "data_type": "bigint",
          "nullable": true,
          "is_primary_key": false,
          "is_foreign_key": true,
          "foreign_table": "core.organization_unit",
          "foreign_column": "id"
        }
      },
      "primary_key": ["id"]
    }
  },
  "relationships": [
    {
      "from": "identity.user_account.primary_org_unit_id",
      "to": "core.organization_unit.id",
      "type": "many-to-one"
    }
  ]
}
```

---

## How It's Used in the Chat Application

### 1. Schema Retrieval

When a user asks a question, the system:
1. **Retrieves relevant schema chunks** using semantic search (RAG)
2. **Finds related tables** based on the question context
3. **Provides focused context** to the LLM (only relevant tables/relationships)

### 2. SQL Generation

The LLM uses the retrieved schema context to:
1. **Understand table structures** (columns, data types)
2. **Follow relationships** (foreign keys, joins)
3. **Generate accurate SQL queries** based on the schema graph

### 3. Architecture Explanation

The architecture overview chunk helps the LLM:
1. **Explain business flows** by understanding entity relationships
2. **Synthesize high-level architecture** from detailed schema
3. **Answer "how does it work" questions** comprehensively

---

## Visual Representation

### Graph Structure

```
┌─────────────────────┐
│  SchemaGraph        │
│                     │
│  tables: {          │
│    "identity.user": │
│      Table(...)     │
│  }                  │
│                     │
│  relationships: [   │
│    Relationship(...)│
│  ]                  │
│                     │
│  schemas: {         │
│    "core",          │
│    "identity", ...  │
│  }                  │
└─────────────────────┘
         │
         │ contains
         ▼
┌─────────────────────┐
│  Table              │
│  - schema           │
│  - name             │
│  - columns: {       │
│      Column(...)    │
│    }                │
│  - primary_key      │
└─────────────────────┘
         │
         │ contains
         ▼
┌─────────────────────┐
│  Column             │
│  - name             │
│  - data_type        │
│  - is_foreign_key   │
│  - foreign_table    │
└─────────────────────┘
         │
         │ references
         ▼
┌─────────────────────┐
│  Relationship       │
│  - from_table       │
│  - from_column      │
│  - to_table         │
│  - to_column        │
│  - relationship_type│
└─────────────────────┘
```

### Example Graph Visualization

```
identity.user_account
    │
    │ primary_org_unit_id (FK)
    ▼
core.organization_unit
    │
    │ region_id (FK)
    ▼
core.region
    │
    │ tenant_id (FK)
    ▼
core.tenant

identity.user_account
    │
    │ user_id (FK)
    ▼
identity.user_role_assignment
    │
    │ role_id (FK)
    ▼
identity.functional_role
```

---

## Benefits of This Approach

1. **Automatic Schema Understanding**: No manual documentation needed
2. **Relationship Discovery**: Automatically finds all foreign key relationships
3. **Context-Aware Retrieval**: RAG retrieves only relevant schema parts
4. **Accurate SQL Generation**: LLM understands table structures and relationships
5. **Scalable**: Works with 100+ tables without manual configuration

---

## Files Involved

1. **`schema_parser.py`**: Parses DDL and builds the graph structure
2. **`schema_graph.py`**: Converts graph to chunks and stores in vector DB
3. **`schema_retrieval.py`**: Retrieves relevant schema chunks using RAG
4. **`sql_generate_v2.py`**: Uses retrieved schema to generate SQL

---

## Summary

The knowledge graph in this codebase is a **structured representation of the database schema** that:

- **Nodes** = Tables (with columns as properties)
- **Edges** = Foreign key relationships
- **Properties** = Column metadata (type, nullable, FK references)

This enables the chat application to:
- Understand database structure automatically
- Generate accurate SQL queries
- Explain business architecture
- Answer complex questions about data relationships

The graph is parsed from DDL, stored as vector embeddings, and retrieved contextually to provide intelligent, schema-aware responses.

