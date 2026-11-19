from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ModelInfo(BaseModel):
    id: str = Field(..., description="Unique model identifier, e.g. gpt-4o, gemini-2.0-flash")
    name: str = Field(..., description="Display name for the model")
    provider: str = Field(..., description="Provider name: openai, gemini, openrouter, cheaper_inference")
    capabilities: List[str] = Field(default_factory=list, description="Supported capabilities: llm, stt, tts, voice")
    context_window: int = Field(default=8192, description="Maximum token context window")
    input_cost_per_million: float = Field(default=0.0, description="Cost in USD per 1M input tokens")
    output_cost_per_million: float = Field(default=0.0, description="Cost in USD per 1M output tokens")
    supports_streaming: bool = Field(default=True)
    supports_vision: bool = Field(default=False)
    description: Optional[str] = None

class VoiceInfo(BaseModel):
    id: str = Field(..., description="Voice identifier, e.g. alloy, ar-XA-Standard-A, ar-EG-SalmaNeural")
    name: str = Field(..., description="Display name")
    provider: str = Field(..., description="Provider name: openai, gemini, edge_tts")
    language: str = Field(..., description="Language code: en, ar, or en-US, ar-SA, etc.")
    gender: Optional[str] = Field(default="neutral", description="male, female, neutral")
    description: Optional[str] = None

class ProviderStatus(BaseModel):
    provider: str
    name: str
    is_configured: bool = False
    is_healthy: bool = False
    error: Optional[str] = None
    supported_capabilities: List[str] = Field(default_factory=list)
    models: List[ModelInfo] = Field(default_factory=list)
    voices: List[VoiceInfo] = Field(default_factory=list)

class ProviderTestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

class ProviderTestResult(BaseModel):
    provider: str
    success: bool
    latency_ms: float
    message: str
    models_found: int = 0
    error: Optional[str] = None
