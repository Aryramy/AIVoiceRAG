import time
import httpx
from typing import List, Dict, Any, Optional
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

class GeminiAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def test_connection(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> ProviderTestResult:
        target_key = api_key or self.api_key
        if not target_key:
            return ProviderTestResult(
                provider=self.provider_name,
                success=False,
                latency_ms=0.0,
                message="Google Gemini API key is missing or not configured.",
                error="MISSING_API_KEY"
            )

        start = time.perf_counter()
        url = f"{self.base_url}/models?key={target_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                latency = round((time.perf_counter() - start) * 1000, 2)
                
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("models", [])
                    return ProviderTestResult(
                        provider=self.provider_name,
                        success=True,
                        latency_ms=latency,
                        message=f"Connected successfully. Discovered {len(models)} Gemini models.",
                        models_found=len(models)
                    )
                else:
                    return ProviderTestResult(
                        provider=self.provider_name,
                        success=False,
                        latency_ms=latency,
                        message=f"Connection failed with status {res.status_code}",
                        error=res.text
                    )
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000, 2)
            return ProviderTestResult(
                provider=self.provider_name,
                success=False,
                latency_ms=latency,
                message=f"Network error: {str(e)}",
                error=str(e)
            )

    async def list_models(self) -> List[ModelInfo]:
        if not self.api_key:
            return []
        
        url = f"{self.base_url}/models?key={self.api_key}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url)
                if res.status_code != 200:
                    return []
                data = res.json().get("models", [])
                
                results: List[ModelInfo] = []
                for m in data:
                    name_raw = m.get("name", "")
                    model_id = name_raw.replace("models/", "")
                    display_name = m.get("displayName", model_id)
                    supported_methods = m.get("supportedGenerationMethods", [])
                    
                    if "generateContent" not in supported_methods:
                        continue
                    
                    capabilities = ["llm"]
                    if "flash" in model_id:
                        in_cost = 0.075
                        out_cost = 0.30
                    elif "pro" in model_id:
                        in_cost = 1.25
                        out_cost = 5.00
                    else:
                        in_cost = 0.10
                        out_cost = 0.40

                    results.append(ModelInfo(
                        id=model_id,
                        name=display_name,
                        provider=self.provider_name,
                        capabilities=capabilities,
                        context_window=m.get("inputTokenLimit", 1048576),
                        input_cost_per_million=in_cost,
                        output_cost_per_million=out_cost,
                        supports_streaming=True,
                        supports_vision=True,
                        description=m.get("description", "")
                    ))
                
                results.sort(key=lambda x: (not "flash" in x.id, x.name))
                return results
        except Exception:
            return []

    async def list_voices(self) -> List[VoiceInfo]:
        # Gemini 2.0 Live voices (Puck, Charon, Kore, Fenrir, Aoede)
        voices = ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]
        return [
            VoiceInfo(
                id=v.lower(),
                name=f"Gemini {v}",
                provider=self.provider_name,
                language="multilingual",
                gender="neutral",
                description=f"Gemini Multimodal Live Voice: {v}"
            )
            for v in voices
        ]

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> Any:
        # We use Gemini's official OpenAI-compatible endpoint
        url = f"{self.base_url}/openai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        clean_model = model.replace("models/", "")
        payload = {
            "model": clean_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            if not stream:
                res = await client.post(url, headers=headers, json=payload)
                res.raise_for_status()
                return res.json()
            else:
                async def stream_generator():
                    async with client.stream("POST", url, headers=headers, json=payload) as response:
                        response.raise_for_status()
                        import json
                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if data_str == "[DONE]":
                                    break
                                try:
                                    chunk = json.loads(data_str)
                                    delta = chunk["choices"][0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield delta
                                except Exception:
                                    continue
                return stream_generator()

