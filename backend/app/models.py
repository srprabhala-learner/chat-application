from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="user|assistant")
    content: str


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str


class Citation(BaseModel):
    source_path: str
    chunk_id: str


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[Citation] = []


