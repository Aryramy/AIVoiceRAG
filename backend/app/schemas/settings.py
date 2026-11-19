from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class AISettingsBase(BaseModel):
    # LLM
    llm_provider: str = Field(default="openai", description="Active LLM provider")
    llm_model: str = Field(default="gpt-4o", description="Active LLM model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32768)
    
    # STT
    stt_provider: str = Field(default="openai", description="Active STT provider")
    stt_model: str = Field(default="whisper-1", description="Active STT model ID")
    
    # TTS
    tts_provider: str = Field(default="edge_tts", description="Active TTS provider")
    tts_voice_en: str = Field(default="en-US-JennyNeural", description="English TTS voice")
    tts_voice_ar: str = Field(default="ar-SA-HamedNeural", description="Arabic TTS voice")
    
    # Realtime Voice
    voice_provider: str = Field(default="openai", description="Active Realtime Voice provider")
    voice_model: str = Field(default="gpt-4o-realtime-preview", description="Realtime voice model")
    
    # Routing
    routing_strategy: str = Field(default="smart_auto", description="smart_auto, manual, low_cost, high_quality, max_capability")
    fallback_enabled: bool = Field(default=True)
    fallback_provider: Optional[str] = Field(default="openrouter")
    fallback_model: Optional[str] = Field(default="openai/gpt-4o-mini")
    
    # RAG parameters
    similarity_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=20)
    hybrid_alpha: float = Field(default=0.6, ge=0.0, le=1.0, description="Dense vs sparse weight (1.0 = pure dense)")
    reranker_enabled: bool = Field(default=True)
    abstention_enabled: bool = Field(default=True)
    
    # System Prompts
    system_prompt_en: str = Field(
        default="You are VoiceRag, an enterprise AI voice and knowledge assistant. Provide clear, accurate, and grounded answers citing sources where appropriate.",
        description="Default English system prompt"
    )
    system_prompt_ar: str = Field(
        default="أنت VoiceRag، المساعد الصوتي والمعرفي الذكي للمؤسسات. قدّم إجابات واضحة ودقيقة ومستندة إلى المصادر المتاحة مع ذكر المراجع المناسبة.",
        description="Default Arabic system prompt"
    )
    
    # Safety & Limits
    monthly_budget_usd: float = Field(default=100.0, ge=0.0)
    rate_limit_per_minute: int = Field(default=60, ge=1)

class AISettingsUpdate(BaseModel):
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    stt_provider: Optional[str] = None
    stt_model: Optional[str] = None
    
    tts_provider: Optional[str] = None
    tts_voice_en: Optional[str] = None
    tts_voice_ar: Optional[str] = None
    
    voice_provider: Optional[str] = None
    voice_model: Optional[str] = None
    
    routing_strategy: Optional[str] = None
    fallback_enabled: Optional[bool] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    
    similarity_threshold: Optional[float] = None
    top_k: Optional[int] = None
    hybrid_alpha: Optional[float] = None
    reranker_enabled: Optional[bool] = None
    abstention_enabled: Optional[bool] = None
    
    system_prompt_en: Optional[str] = None
    system_prompt_ar: Optional[str] = None
    
    monthly_budget_usd: Optional[float] = None
    rate_limit_per_minute: Optional[int] = None

class AISettingsResponse(AISettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: str = "default"
    user_id: Optional[str] = None
    created_at: Any = None
    updated_at: Any = None
