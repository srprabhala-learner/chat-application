from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load .env from the backend folder regardless of current working directory
    _env_path = Path(__file__).resolve().parents[1] / ".env"
    model_config = SettingsConfigDict(env_file=_env_path, extra="ignore")

    # Postgres (reuse entitlements DB by default)
    pg_host: str = Field(default="localhost", validation_alias="PG_HOST")
    pg_port: int = Field(default=5432, validation_alias="PG_PORT")
    pg_db: str = Field(default="entitlements_platform", validation_alias="PG_DB")
    pg_user: str = Field(default="entitlements_user", validation_alias="PG_USER")
    pg_password: str = Field(default="entitlements_pass", validation_alias="PG_PASSWORD")

    # RAG storage schema/table
    rag_schema: str = Field(default="rag", validation_alias="RAG_SCHEMA")
    rag_table: str = Field(default="documents", validation_alias="RAG_TABLE")

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # OpenAI
    # Supports either:
    # - OPENAI_API_KEY=...
    # - openai_api_key=...
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")

    # Service
    host: str = "0.0.0.0"
    port: int = 8000
    cors_allow_origins: str = "*"  # set to http://localhost:3000 in production

    # Implementation Mode
    # Options: "option1", "option2", "option3", "option4", "legacy" (default)
    # - option1: Enhanced RAG + Structured Schema Understanding
    # - option2: Agentic Architecture (LangChain/LangGraph)
    # - option3: Fine-Tuned Text-to-SQL Model
    # - option4: Hybrid (All of the above)
    # - legacy: Current template-based approach
    mode_of_implementation: str = Field(
        default="legacy",
        validation_alias="MODE_OF_IMPLEMENTATION"
    )


settings = Settings()


