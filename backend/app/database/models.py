import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    preferred_language = Column(String(10), default="en")  # en, ar
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), default="New Conversation")
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=True)
    language = Column(String(10), default="en")  # en, ar
    mode = Column(String(50), default="hybrid")  # chat, voice, rag_strict, rag_first
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    knowledge_base = relationship("KnowledgeBase", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    intent = Column(String(50), default="knowledge")
    language = Column(String(10), default="en")  # en, ar
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    audio_url = Column(String(500), nullable=True)
    audio_duration_seconds = Column(Float, default=0.0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
    citations = relationship("MessageCitation", back_populates="message", cascade="all, delete-orphan")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(20), default="multilingual")
    embedding_model = Column(String(255), default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
    vector_dimension = Column(Integer, default=384)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    documents = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="knowledge_base")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="Untitled")
    file_name = Column(String(255), nullable=True)
    file_type = Column(String(50), default="txt")  # pdf, docx, xlsx, txt, md, url
    file_size_bytes = Column(Integer, default=0)
    file_path = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=True)
    language = Column(String(10), default="en")
    status = Column(String(50), default="indexed")  # pending, processing, indexed, failed
    chunk_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    knowledge_base = relationship("KnowledgeBase", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_heading = Column(String(255), nullable=True)
    token_count = Column(Integer, default=0)
    qdrant_point_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class MessageCitation(Base):
    __tablename__ = "message_citations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    document_title = Column(String(255), nullable=True)
    chunk_id = Column(String(36), ForeignKey("document_chunks.id"), nullable=True)
    content_snippet = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    similarity_score = Column(Float, default=0.0)

    message = relationship("Message", back_populates="citations")


class AISettings(Base):
    __tablename__ = "ai_settings"

    id = Column(String(36), primary_key=True, default="default")
    user_id = Column(String(36), nullable=True)
    
    # LLM
    llm_provider = Column(String(50), default="openai")
    llm_model = Column(String(100), default="gpt-4o-mini")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2048)
    
    # STT
    stt_provider = Column(String(50), default="openai")
    stt_model = Column(String(100), default="whisper-1")
    
    # TTS
    tts_provider = Column(String(50), default="edge_tts")
    tts_voice_en = Column(String(100), default="en-US-JennyNeural")
    tts_voice_ar = Column(String(100), default="ar-SA-HamedNeural")
    
    # Realtime Voice
    voice_provider = Column(String(50), default="openai")
    voice_model = Column(String(100), default="gpt-4o-realtime-preview")
    
    # Routing
    routing_strategy = Column(String(50), default="smart_auto")
    fallback_enabled = Column(Boolean, default=True)
    fallback_provider = Column(String(50), default="openrouter")
    fallback_model = Column(String(100), default="openai/gpt-4o-mini")
    
    # RAG parameters
    similarity_threshold = Column(Float, default=0.45)
    top_k = Column(Integer, default=5)
    hybrid_alpha = Column(Float, default=0.6)
    reranker_enabled = Column(Boolean, default=True)
    abstention_enabled = Column(Boolean, default=True)
    
    # Prompts
    system_prompt_en = Column(Text, default="You are VoiceRag, an enterprise AI voice and knowledge assistant. Provide clear, accurate, and grounded answers citing sources where appropriate.")
    system_prompt_ar = Column(Text, default="أنت VoiceRag، المساعد الصوتي والمعرفي الذكي للمؤسسات. قدّم إجابات واضحة ودقيقة ومستندة إلى المصادر المتاحة مع ذكر المراجع المناسبة.")
    
    # Limits
    monthly_budget_usd = Column(Float, default=100.0)
    rate_limit_per_minute = Column(Integer, default=60)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=True)
    conversation_id = Column(String(36), nullable=True, index=True)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    capability = Column(String(50), nullable=False)  # llm, stt, tts, voice
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    audio_seconds = Column(Float, default=0.0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, default=0.0)
    status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
