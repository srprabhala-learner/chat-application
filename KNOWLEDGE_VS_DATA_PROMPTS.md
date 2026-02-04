# Knowledge vs Data Prompts: Classification Guide

## Overview

The intent classifier categorizes user prompts into two main types:
1. **Knowledge** (`knowledge_only`): Questions about how the system works, architecture, concepts
2. **Data** (`generic_sql` and other SQL intents): Questions that require querying the database for specific values

## Knowledge Prompts (`knowledge_only` Intent)

Knowledge prompts are questions that ask for **explanations, concepts, architecture, or how things work** - not specific data values.

### Characteristics

- Ask "how" or "why" something works
- Request explanations or descriptions
- Ask about architecture, design, or concepts
- Seek understanding of relationships or processes
- Do NOT ask for specific data values (names, counts, lists, etc.)

### Examples of Knowledge Prompts

#### Architecture & Design Questions

✅ **"Explain how entitlements are evaluated at login."**
- Asks about the process/workflow
- No specific data requested

✅ **"Can you explain in detail the different entities of the entitlements platform and thereby give me a high level business flow?"**
- Asks for architecture explanation
- Requests understanding of entities and relationships

✅ **"How does the entitlement evaluation process work?"**
- Asks about the process
- No specific data values

✅ **"What is the architecture of the entitlements platform?"**
- Asks for system architecture
- Conceptual question

#### System Understanding Questions

✅ **"How are applications related to departments?"**
- Asks about relationships/concepts
- Not asking for specific data

✅ **"Explain the relationship between users, roles, and applications."**
- Asks for conceptual understanding
- No specific values requested

✅ **"What are the different domains in the entitlements platform?"**
- Asks about system structure
- Conceptual question

#### Process & Workflow Questions

✅ **"How does a user get access to an application?"**
- Asks about the process
- No specific data

✅ **"What happens when a user logs in?"**
- Asks about workflow
- Conceptual question

✅ **"Explain the policy evaluation flow."**
- Asks about process
- No specific data values

#### Concept & Definition Questions

✅ **"What is a policy set?"**
- Asks for definition/explanation
- Conceptual question

✅ **"What does application availability mean?"**
- Asks for concept explanation
- No specific data

✅ **"Explain what toxic combinations are."**
- Asks for concept explanation
- Conceptual question

### Keywords That Indicate Knowledge Prompts

The system also detects architecture questions using these keywords:
- `architecture`
- `entities`
- `business flow`
- `how does`
- `explain`
- `overview`
- `structure`
- `relationship`
- `domain`
- `component`
- `detail`
- `different entities`
- `high level`

## Data Prompts (NOT Knowledge)

These are questions that require **querying the database** for specific values and should be classified as `generic_sql` or other SQL intents.

### Characteristics

- Ask for specific data values (names, emails, counts, lists)
- Request information about specific records
- Ask "what is", "who is", "show me", "list", "count"
- Require SQL queries to answer

### Examples of Data Prompts (NOT Knowledge)

❌ **"What is the name of user whose username is user00001?"**
- Asks for specific data value
- Classified as: `generic_sql`

❌ **"Show me the email of user user00001"**
- Asks for specific data
- Classified as: `generic_sql`

❌ **"How many users are in Department 1?"**
- Asks for count (specific data)
- Classified as: `users_in_dept`

❌ **"List all applications"**
- Asks for specific data list
- Classified as: `generic_sql`

❌ **"What is the policy rule for application with app code APP_1?"**
- Asks for specific data
- Classified as: `generic_sql`

❌ **"Show users from DEPT_5"**
- Asks for specific data list
- Classified as: `users_in_dept`

❌ **"Which departments have access to Application 1?"**
- Asks for specific data
- Classified as: `departments_for_app`

## Key Distinction

### Knowledge = "How/Why/What is the concept?"
- Explains how something works
- Describes architecture or design
- Explains relationships or processes
- No specific data values needed

### Data = "What is the value/Who is/Show me/List/Count"
- Requests specific data values
- Needs database queries
- Asks for names, emails, counts, lists
- Requires SQL execution

## Classification Rules

From the intent classifier system prompt:

> **"knowledge_only: pure documentation / explanation questions (e.g., 'how does it work', 'explain the architecture')"**
>
> **"IMPORTANT: Questions asking for specific data values (names, emails, counts, lists) should be classified as 'generic_sql', NOT 'knowledge_only'."**

## How It Works

1. **Intent Classification**: The LLM classifies the prompt into one of the intents
2. **Knowledge Detection**: If classified as `knowledge_only`, OR if keywords suggest architecture questions
3. **RAG Retrieval**: System retrieves relevant documentation/schema chunks
4. **Answer Generation**: LLM synthesizes answer from retrieved context (no SQL execution)

## Examples Comparison

| Knowledge Prompt | Data Prompt |
|-----------------|-------------|
| "How are entitlements evaluated?" | "What entitlements does user00001 have?" |
| "Explain the relationship between users and departments" | "Which users are in DEPT_5?" |
| "What is the architecture of the system?" | "What is the name of application APP_1?" |
| "How does policy evaluation work?" | "What is the policy rule for APP_1?" |
| "Explain the business flow" | "Show me all applications" |

## Summary

**Knowledge prompts** are about:
- ✅ Concepts and explanations
- ✅ Architecture and design
- ✅ Processes and workflows
- ✅ Relationships and how things work
- ❌ NOT specific data values

**Data prompts** are about:
- ✅ Specific values (names, emails, counts)
- ✅ Lists and records
- ✅ Information about specific entities
- ❌ NOT concepts or explanations

The system uses RAG (Retrieval Augmented Generation) for knowledge prompts, retrieving relevant documentation and schema information to provide comprehensive explanations without executing SQL queries.

