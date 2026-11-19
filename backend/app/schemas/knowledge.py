from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    title: str = "Untitled"
    file_name: Optional[str] = None
    file_type: str = "txt"
    file_size_bytes: int = 0
    status: str = "indexed"
    chunk_count: int = 0
    language: Optional[str] = "en"
    created_at: Any = None
    error_message: Optional[str] = None

class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    language: Optional[str] = "multilingual"

class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    language: Optional[str] = "multilingual"
    document_count: int = 0
    chunk_count: int = 0
    created_at: Any = None
    updated_at: Any = None
    documents: List[DocumentResponse] = []

class RetrievalQueryRequest(BaseModel):
    query: str
    top_k: int = 5
    hybrid_alpha: float = 0.6
    similarity_threshold: float = 0.35

class RetrievalResultResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    page_number: Optional[int] = None
    score: float = 0.0
    dense_rank: Optional[int] = None
    sparse_rank: Optional[int] = None
