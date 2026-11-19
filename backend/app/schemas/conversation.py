from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    page_number: Optional[int] = None
    content_snippet: Optional[str] = None
    similarity_score: float = 0.0

class MessageCreate(BaseModel):
    content: str
    language: Optional[str] = None
    audio_base64: Optional[str] = None
    stream: bool = False

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    language: Optional[str] = "en"
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created_at: Any = None
    citations: List[CitationResponse] = []

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    language: Optional[str] = "en"

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    title: str
    language: str = "en"
    created_at: Any = None
    updated_at: Any = None
    message_count: int = 0
