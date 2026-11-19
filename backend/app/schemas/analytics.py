from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class UsageLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    provider: str
    model: str
    capability: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    audio_seconds: float = 0.0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None
    created_at: Any = None

class ModelUsageStat(BaseModel):
    model: str
    provider: str
    calls_count: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float

class AnalyticsSummary(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost_usd: float
    avg_latency_ms: float
    error_rate_percentage: float
    by_provider: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    by_capability: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    top_models: List[ModelUsageStat] = Field(default_factory=list)
    recent_logs: List[UsageLogResponse] = Field(default_factory=list)
