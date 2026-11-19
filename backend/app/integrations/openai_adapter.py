import time
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

class OpenAIAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")

    @property
    def provider_name(self) -> str:
        return "openai"

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
                message="OpenAI API key is missing or not configured.",
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
                    capabilities = []
                    context_window = 8192
                    in_cost = 0.0
                    out_cost = 0.0
                    
                    if "gpt-4o-mini" in model_id:
                        capabilities = ["llm"]
                        context_window = 128000
                        in_cost = 0.15
                        out_cost = 0.60
                    elif "gpt-4o" in model_id and "realtime" not in model_id:
                        capabilities = ["llm"]
                        context_window = 128000
                        in_cost = 2.50
                        out_cost = 10.00
                    elif "realtime" in model_id:
                        capabilities = ["voice", "llm"]
                        context_window = 128000
                        in_cost = 5.00
                        out_cost = 20.00
                    elif "o1" in model_id or "o3" in model_id:
                        capabilities = ["llm"]
                        context_window = 200000
                        in_cost = 15.00
                        out_cost = 60.00
                    elif "whisper" in model_id:
                        capabilities = ["stt"]
                    elif "tts" in model_id:
                        capabilities = ["tts"]
                    elif "gpt-3.5" in model_id or "gpt-4" in model_id:
                        capabilities = ["llm"]
                    else:
                        continue # Filter non-chat/audio auxiliary models
                    
                    results.append(ModelInfo(
                        id=model_id,
                        name=model_id,
                        provider=self.provider_name,
                        capabilities=capabilities,
                        context_window=context_window,
                        input_cost_per_million=in_cost,
                        output_cost_per_million=out_cost,
                        supports_streaming=True,
                        supports_vision="4o" in model_id or "o1" in model_id
                    ))
                
                # Sort prioritizing gpt-4o, gpt-4o-mini, o1
                results.sort(key=lambda x: (not x.id.startswith("gpt-4o"), x.id))
                return results
        except Exception:
            return []

    async def list_voices(self) -> List[VoiceInfo]:
        voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
        return [
            VoiceInfo(
                id=v,
                name=v.capitalize(),
                provider=self.provider_name,
                language="multilingual",
                gender="neutral" if v in ["alloy", "fable"] else ("male" if v in ["echo", "onyx"] else "female"),
                description=f"OpenAI Neural voice: {v}"
            )
            for v in voices
        ]

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
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

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language: Optional[str] = None) -> str:
        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": "whisper-1"}
        if language:
            data["language"] = language
        
        files = {"file": (filename, audio_bytes, "audio/wav")}
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, data=data, files=files)
            res.raise_for_status()
            return res.json().get("text", "")

    async def synthesize_speech(self, text: str, voice: str = "alloy", model: str = "tts-1") -> bytes:
        url = f"{self.base_url}/audio/speech"
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=self._headers(), json=payload)
            res.raise_for_status()
            return res.content

