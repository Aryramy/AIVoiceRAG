import time
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

OPENAI_NATIVE_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"
]

class OpenAIAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0), limits=limits)
        return self._client
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
                    
                    if "gpt-4o-mini" in model_id and "transcribe" not in model_id and "tts" not in model_id:
                        capabilities = ["llm"]
                        context_window = 128000
                        in_cost = 0.15
                        out_cost = 0.60
                    elif "gpt-4o" in model_id and "realtime" not in model_id and "transcribe" not in model_id and "tts" not in model_id:
                        capabilities = ["llm"]
                        context_window = 128000
                        in_cost = 2.50
                        out_cost = 10.00
                    elif ("whisper" in model_id or "transcribe" in model_id) and not any(k in model_id.lower() for k in ["tts", "speech"]):
                        capabilities = ["stt"]
                    elif "tts" in model_id:
                        capabilities = ["tts"]
                    elif "realtime" in model_id:
                        capabilities = ["voice"]
                        context_window = 128000
                        in_cost = 5.00
                        out_cost = 20.00
                    elif "o1" in model_id or "o3" in model_id:
                        capabilities = ["llm"]
                        context_window = 200000
                        in_cost = 15.00
                        out_cost = 60.00
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
                
                # Ensure STT & TTS models are explicitly included if omitted by live /v1/models response
                discovered_ids = {r.id for r in results}
                known_audio_models = [
                    ("whisper-1", ["stt"]),
                    ("gpt-4o-transcribe", ["stt"]),
                    ("gpt-4o-mini-transcribe", ["stt"]),
                    ("tts-1", ["tts"]),
                    ("tts-1-hd", ["tts"]),
                    ("gpt-4o-mini-tts", ["tts"]),
                ]
                for am_id, caps in known_audio_models:
                    if am_id not in discovered_ids:
                        results.append(ModelInfo(
                            id=am_id,
                            name=am_id,
                            provider=self.provider_name,
                            capabilities=caps,
                            context_window=8192,
                            input_cost_per_million=0.0,
                            output_cost_per_million=0.0,
                            supports_streaming=True,
                            supports_vision=False
                        ))

                # Sort prioritizing gpt-4o, gpt-4o-mini, o1
                results.sort(key=lambda x: (not x.id.startswith("gpt-4o"), x.id))
                return results
        except Exception:
            return []

    async def list_voices(self) -> List[VoiceInfo]:
        return [
            VoiceInfo(
                id=v,
                name=v.capitalize(),
                provider=self.provider_name,
                language="multilingual",
                gender="neutral" if v in ["alloy", "fable", "ballad", "verse"] else ("male" if v in ["echo", "onyx", "ash"] else "female"),
                description=f"OpenAI Neural voice: {v.capitalize()}"
            )
            for v in OPENAI_NATIVE_VOICES
        ]

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        is_voice: bool = False,
        **kwargs: Any
    ) -> Any:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        if is_voice and any(r in model.lower() for r in ["o1", "o3"]):
            payload["reasoning_effort"] = "low"

        if not stream:
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, headers=self._headers(), json=payload)
                res.raise_for_status()
                return res.json()
        else:
            async def stream_generator():
                async with httpx.AsyncClient(timeout=60.0) as stream_client:
                    async with stream_client.stream("POST", url, headers=self._headers(), json=payload) as response:
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
        if language and language.strip().lower() not in ["auto", "multilingual", "none"]:
            data["language"] = language.strip().lower()
        
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

    async def stream_synthesize(self, text: str, voice: str = "alloy", model: str = "tts-1") -> AsyncIterator[bytes]:
        url = f"{self.base_url}/audio/speech"
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3"
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, headers=self._headers(), json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    yield chunk
