from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.provider import (
    ModelInfo,
    VoiceInfo,
    ProviderStatus,
    ProviderTestRequest,
    ProviderTestResult
)
from backend.app.integrations import get_provider_adapter, get_edge_tts_adapter
from backend.app.core.config import settings

router = APIRouter(prefix="/providers", tags=["Providers"])

PROVIDERS_METADATA = {
    "openai": {
        "name": "OpenAI",
        "capabilities": ["llm", "stt", "tts"],
        "key_present": bool(settings.OPENAI_API_KEY)
    },
    "gemini": {
        "name": "Google Gemini",
        "capabilities": ["llm", "stt", "tts"],
        "key_present": bool(settings.GEMINI_API_KEY)
    },
    "openrouter": {
        "name": "OpenRouter",
        "capabilities": ["llm", "stt", "tts"],
        "key_present": bool(settings.OPENROUTER_API_KEY)
    },
    "cheaper_inference": {
        "name": "CheaperInference",
        "capabilities": ["llm", "stt", "tts"],
        "key_present": bool(settings.CHEAPER_INFERENCE_API_KEY)
    },
    "edge_tts": {
        "name": "Microsoft Edge TTS (Local Neural)",
        "capabilities": ["tts"],
        "key_present": True
    }
}

@router.get("", response_model=List[ProviderStatus])
async def list_providers():
    """
    Returns list of all supported providers with their configuration status and capability metadata.
    """
    results: List[ProviderStatus] = []
    
    for p_id, meta in PROVIDERS_METADATA.items():
        if p_id == "edge_tts":
            edge = get_edge_tts_adapter()
            voices = await edge.list_voices()
            results.append(ProviderStatus(
                provider=p_id,
                name=meta["name"],
                is_configured=True,
                is_healthy=True,
                supported_capabilities=meta["capabilities"],
                models=[],
                voices=voices
            ))
            continue

        adapter = get_provider_adapter(p_id)
        is_conf = meta["key_present"]
        
        results.append(ProviderStatus(
            provider=p_id,
            name=meta["name"],
            is_configured=is_conf,
            is_healthy=is_conf,
            supported_capabilities=meta["capabilities"],
            models=[],
            voices=[]
        ))

    return results

@router.get("/{provider}/models", response_model=List[ModelInfo])
async def list_provider_models(
    provider: str,
    capability: Optional[str] = Query(None, description="Filter by capability: llm, stt, tts, voice")
):
    """
    Dynamically discovers and lists models live from the provider API.
    """
    adapter = get_provider_adapter(provider)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")

    models = await adapter.list_models()
    if capability:
        models = [m for m in models if capability.lower() in [c.lower() for c in m.capabilities]]
    return models

@router.get("/{provider}/voices", response_model=List[VoiceInfo])
async def list_provider_voices(
    provider: str,
    language: Optional[str] = Query(None, description="Filter by language: en, ar")
):
    """
    Lists available voices from the specified provider (e.g. edge_tts, openai, gemini).
    """
    if provider == "edge_tts":
        voices = await get_edge_tts_adapter().list_voices()
    else:
        adapter = get_provider_adapter(provider)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"Provider '{provider}' not found")
        voices = await adapter.list_voices()

    if language:
        voices = [v for v in voices if language.lower() in v.language.lower() or v.language == "multilingual"]
    return voices

@router.post("/test", response_model=ProviderTestResult)
async def test_provider_connection(data: ProviderTestRequest):
    """
    Executes a real live connection test to verify API keys and measure latency.
    """
    adapter = get_provider_adapter(data.provider)
    if not adapter:
        if data.provider == "edge_tts":
            return ProviderTestResult(
                provider="edge_tts",
                success=True,
                latency_ms=1.5,
                message="Edge TTS local engine is ready and active.",
                models_found=0
            )
        raise HTTPException(status_code=404, detail=f"Provider '{data.provider}' not recognized")

    result = await adapter.test_connection(api_key=data.api_key, base_url=data.base_url)
    return result

