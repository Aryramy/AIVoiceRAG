import time
import httpx
from typing import List, Dict, Any, Optional
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

class CheaperInferenceAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.CHEAPER_INFERENCE_API_KEY
        self.base_url = (base_url or settings.CHEAPER_INFERENCE_BASE_URL or "https://api.cheaperinference.com/v1").rstrip("/")

    @property
    def provider_name(self) -> str:
        return "cheaper_inference"

    def _headers(self, override_key: Optional[str] = None) -> Dict[str, str]:
        key = override_key or self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    async def test_connection(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> ProviderTestResult:
        target_url = (base_url or self.base_url).rstrip("/") + "/models"
        target_key = api_key or self.api_key
        
        if not target_key:
            return ProviderTestResult(
                provider=self.provider_name,
                success=False,
                latency_ms=0.0,
                message="CheaperInference API key is missing or not configured.",
                error="MISSING_API_KEY"
            )

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(target_url, headers=self._headers(target_key))
                latency = round((time.perf_counter() - start) * 1000, 2)
                
                if res.status_code == 200:
                    data = res.json()
                    models = data.get("data", [])
                    return ProviderTestResult(
                        provider=self.provider_name,
                        success=True,
                        latency_ms=latency,
                        message=f"Connected successfully. Discovered {len(models)} models.",
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
        
        url = f"{self.base_url}/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=self._headers())
                if res.status_code != 200:
                    return []
                data = res.json().get("data", [])
                
                results: List[ModelInfo] = []
                for m in data:
                    model_id = m.get("id", "")
                    name = m.get("name", model_id)
                    results.append(ModelInfo(
                        id=model_id,
                        name=name,
                        provider=self.provider_name,
                        capabilities=["llm"],
                        context_window=m.get("context_length", 32768),
                        input_cost_per_million=0.10,
                        output_cost_per_million=0.20,
                        supports_streaming=True,
                        supports_vision=False
                    ))
                return results
        except Exception:
            return []

    async def list_voices(self) -> List[VoiceInfo]:
        return []

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> Any:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            if not stream:
                res = await client.post(url, headers=self._headers(), json=payload)
                res.raise_for_status()
                return res.json()
            else:
                async def stream_generator():
                    async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
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
