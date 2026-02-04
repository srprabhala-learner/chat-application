# Architecture Explanation Enhancement

## Problem

The chat application was unable to explain the high-level business architecture and entity relationships of the entitlements platform. When asked questions like:

> "Can you explain in detail the different entities of the entitlements platform and thereby give me a high level business flow"

The system responded with:

> "It seems that there is no specific documentation or context provided regarding the entities of the entitlements platform or the high-level business flow..."

## Root Cause

1. **Missing Architecture Documentation**: While the database schema was available, there was no comprehensive business architecture document that explained:
   - Entity domains and their purposes
   - Relationships between entities
   - Business flows and processes
   - How the system works at a high level

2. **Insufficient Context Retrieval**: The RAG system wasn't retrieving enough context for architecture questions, and wasn't prioritizing architecture-related chunks.

3. **Limited LLM Prompting**: The LLM prompt didn't explicitly instruct the system to synthesize schema information into business architecture explanations.

## Solution

### 1. Created Comprehensive Architecture Document

**File**: `entitlements-app/BUSINESS_ARCHITECTURE.md`

This document provides:
- **Core Business Flow**: Step-by-step explanation of how entitlements are evaluated
- **Entity Domains**: Detailed breakdown of 5 domains:
  - Core Organization Structure
  - Identity & Access
  - Application Catalog
  - Entitlements & Policies
  - Audit & Analytics
- **Entity Relationships**: Hierarchical and cross-domain relationships
- **Business Scenarios**: Real-world use cases (onboarding, deployment, role changes, exceptions)
- **Key Design Principles**: Multi-tenancy, temporal validity, hierarchical scoping, etc.
- **Data Flow Summary**: Visual representation of the entitlement evaluation process

### 2. Enhanced Schema Graph Builder

**File**: `backend/app/schema_graph.py`

Added `_generate_architecture_overview()` method that:
- Synthesizes a high-level architecture overview from the parsed schema
- Groups tables by domain (core, identity, catalog, entitlement, audit, analytics)
- Describes key relationships between entities
- Creates a dedicated architecture chunk that gets stored in the vector database

This ensures that even if the BUSINESS_ARCHITECTURE.md file isn't ingested, the system can still generate architecture explanations from the schema itself.

### 3. Enhanced Schema Retrieval

**File**: `backend/app/schema_retrieval.py`

Improved `retrieve_relevant_schema()` to:
- **Detect Architecture Questions**: Identifies questions asking for architecture/overview/explanation
- **Retrieve More Context**: Gets 3x more chunks for architecture questions (15 vs 5)
- **Prioritize Architecture Chunks**: Specifically looks for and prioritizes:
  - `schema:architecture` chunks
  - `BUSINESS_ARCHITECTURE.md` content
  - `README.md` content
- **Better Context Assembly**: Combines multiple schema chunks to provide comprehensive context

### 4. Enhanced LLM Prompting

**File**: `backend/app/llm_openai.py`

Updated the system prompt to:
- **Explicitly Handle Architecture Questions**: Added a dedicated section for architecture/knowledge questions
- **Instruct Synthesis**: Tells the LLM to:
  - Analyze schema and documentation to explain entities, relationships, and flows
  - Synthesize information from multiple chunks
  - Connect the dots between different entities
  - Be detailed and comprehensive for architecture questions
- **Use Schema to Infer Business Architecture**: Even if not explicitly documented, use schema information to explain business architecture

### 5. Enhanced Chat Handler

**File**: `backend/app/chat_handlers.py`

Updated `Option1Handler.handle()` to:
- **Detect Architecture Questions**: Identifies questions asking for architecture/explanation
- **Retrieve Additional Context**: Gets extra chunks specifically for architecture questions
- **Merge Architecture Chunks**: Combines regular RAG hits with architecture-specific chunks
- **Route to RAG**: Routes architecture questions to RAG (knowledge-only) handler for comprehensive answers

## How It Works Now

1. **User asks architecture question**:
   > "Can you explain in detail the different entities of the entitlements platform and thereby give me a high level business flow"

2. **Intent Classification**: Question is classified as `knowledge_only` or detected as architecture question

3. **Enhanced Retrieval**:
   - System retrieves 15 chunks (vs 8 for regular questions)
   - Prioritizes `BUSINESS_ARCHITECTURE.md` and `schema:architecture` chunks
   - Also retrieves relevant schema chunks

4. **LLM Synthesis**:
   - LLM receives comprehensive context about:
     - Entity domains (core, identity, catalog, entitlement, audit)
     - Relationships between entities
     - Business flows
     - Design principles
   - LLM synthesizes this into a detailed, natural language explanation

5. **Response**: User receives a comprehensive explanation covering:
   - All entity domains and their purposes
   - How entities relate to each other
   - The business flow of entitlement evaluation
   - Key design principles

## Testing

To test the enhancement:

1. **Re-ingest the knowledge base** (to include BUSINESS_ARCHITECTURE.md):
   ```bash
   curl -X POST http://localhost:8000/api/ingest
   ```

2. **Ask architecture questions**:
   - "Can you explain in detail the different entities of the entitlements platform and thereby give me a high level business flow"
   - "What are the different domains in the entitlements platform?"
   - "How does the entitlement evaluation process work?"
   - "Explain the relationship between users, departments, and applications"

3. **Verify the response** includes:
   - Entity domains (core, identity, catalog, entitlement, audit)
   - Relationships between entities
   - Business flow explanation
   - Design principles

## Files Modified

1. `entitlements-app/BUSINESS_ARCHITECTURE.md` (NEW)
2. `backend/app/schema_graph.py` (enhanced)
3. `backend/app/schema_retrieval.py` (enhanced)
4. `backend/app/llm_openai.py` (enhanced)
5. `backend/app/chat_handlers.py` (enhanced)

## Future Enhancements

1. **Visual Diagrams**: Generate entity-relationship diagrams from the schema
2. **Interactive Exploration**: Allow users to drill down into specific entities
3. **Flow Diagrams**: Generate process flow diagrams for business scenarios
4. **Domain-Specific Explanations**: Provide deeper explanations for specific domains on request

