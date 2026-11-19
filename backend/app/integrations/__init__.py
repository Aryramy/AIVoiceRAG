from typing import Dict, Any, Optional
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.integrations.openai_adapter import OpenAIAdapter
from backend.app.integrations.gemini_adapter import GeminiAdapter
from backend.app.integrations.openrouter_adapter import OpenRouterAdapter
from backend.app.integrations.cheaper_inference_adapter import CheaperInferenceAdapter
from backend.app.integrations.edge_tts_adapter import EdgeTTSAdapter

_ADAPTERS: Dict[str, BaseProviderAdapter] = {
    "openai": OpenAIAdapter(),
    "gemini": GeminiAdapter(),
    "openrouter": OpenRouterAdapter(),
    "cheaper_inference": CheaperInferenceAdapter(),
}

_TTS_ADAPTER = EdgeTTSAdapter()

def get_provider_adapter(name: str) -> Optional[BaseProviderAdapter]:
    return _ADAPTERS.get(name.lower())

def get_edge_tts_adapter() -> EdgeTTSAdapter:
    return _TTS_ADAPTER

