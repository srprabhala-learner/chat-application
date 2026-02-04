from openai import OpenAI

from app.config import settings
from app.token_tracker import extract_usage_from_response, log_token_usage


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in environment or backend/.env (openai_api_key=...)."
        )
    return OpenAI(api_key=settings.openai_api_key)


def answer_with_context(question: str, context_chunks: list[dict]) -> str:
    """
    Uses OpenAI to answer with provided context.
    context_chunks items: {source_path, chunk_id, content, score}
    """
    context_text = []
    for i, c in enumerate(context_chunks, start=1):
        context_text.append(
            f"[{i}] source={c['source_path']} chunk_id={c['chunk_id']}\n{c['content']}\n"
        )

    system = (
        "You are the Entitlements Platform assistant with deep knowledge of the system architecture. "
        "You see two kinds of context: (1) documentation/code/schema chunks and "
        "(2) optional SQL_TOOL output embedded in the user message. "
        "\n\n"
        "**For Data Questions (with SQL_TOOL output):**\n"
        "- Use SQL_TOOL output as the source of truth for data answers "
        "(counts, lists, criticality, departments, users, etc.)\n"
        "- DO NOT ask the user to run additional queries\n"
        "- Synthesize the data into a natural language answer\n"
        "\n\n"
        "**For Architecture/Knowledge Questions (without SQL_TOOL output):**\n"
        "- Analyze the provided schema and documentation context to explain:\n"
        "  * Entity domains and their purposes\n"
        "  * Relationships between entities\n"
        "  * Business flows and processes\n"
        "  * How the system works at a high level\n"
        "- Synthesize information from multiple schema chunks to provide comprehensive explanations\n"
        "- If schema chunks are provided, use them to explain the architecture even if they're technical\n"
        "- Connect the dots between different entities to explain business flows\n"
        "- Be detailed and comprehensive for architecture questions\n"
        "\n\n"
        "**General Guidelines:**\n"
        "- Be concise for simple questions\n"
        "- Be detailed and comprehensive for architecture/explanation questions\n"
        "- When explaining entities, mention:\n"
        "  * What the entity represents\n"
        "  * How it relates to other entities\n"
        "  * Its role in the business flow\n"
        "- Use the schema information to infer business architecture even if not explicitly documented"
    )

    user = f"""Question:
{question}

Context:
{''.join(context_text)}
"""

    client = _client()
    # Compatibility: some environments may have an older OpenAI client without `responses`.
    if hasattr(client, "responses"):
        resp = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        # Note: responses API may not have usage info
        return resp.output_text.strip()

    # Fallback: Chat Completions API
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    
    # Track token usage and cost
    usage = extract_usage_from_response(resp.usage, model=settings.openai_model)
    if usage:
        log_token_usage(usage, context="answer_with_context")
    
    return (resp.choices[0].message.content or "").strip()


