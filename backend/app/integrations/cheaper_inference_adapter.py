import time
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

CHEAPER_INFERENCE_VOICES = [
    "alloy", "echo", "fable", "onyx", "nova", "shimmer", "ash", "sage", "coral",
    "rachel", "drew", "clyde", "paul", "domi", "dave", "fin", "sarah", "antoni",
    "thomas", "charlie", "george", "emily", "elli", "callum", "patrick", "harry",
    "liam", "dorothy", "josh", "arnold", "charlotte", "alice", "matilda", "james",
    "joseph", "jeremy", "michael", "ethan", "giggle"
]

class CheaperInferenceAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.CHEAPER_INFERENCE_API_KEY
        self.base_url = (base_url or settings.CHEAPER_INFERENCE_BASE_URL or "https://api.cheaperinference.com/v1").rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0), limits=limits)
        return self._client
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
            client = self._get_http_client()
            res = await client.get(url, headers=self._headers())
            if res.status_code != 200:
                return []
            data = res.json().get("data", [])
            
            results: List[ModelInfo] = []
            for m in data:
                model_id = m.get("id", "")
                name = m.get("name", model_id)
                ctx = m.get("context_length")
                context_window = int(ctx) if (ctx is not None and str(ctx).isdigit()) else 32768
                
                m_type = str(m.get("type", "")).lower()
                endpoint = str(m.get("endpoint", "")).lower()
                mid_lower = model_id.lower()
                
                # Filter out embedding, moderation, image, rerank, and non-chat models
                is_non_llm = any(p in mid_lower for p in [
                    "embed", "minilm", "bge", "e5", "rerank", "tts", "whisper",
                    "transcribe", "moderation", "image", "imagen", "dall-e", "flux",
                    "stable-diffusion", "bark", "musicgen", "speech", "realtime"
                ]) or m_type in ["embedding", "rerank", "moderation", "image", "audio"]

                capabilities = []
                if (m_type == "text" or endpoint == "/v1/chat/completions" or not m_type) and not is_non_llm:
                    capabilities.append("llm")
                if (m_type == "transcription" or endpoint == "/v1/audio/transcriptions" or "transcribe" in mid_lower or "whisper" in mid_lower) and not any(k in mid_lower for k in ["tts", "speech"]):
                    capabilities.append("stt")
                if m_type == "speech" or endpoint == "/v1/audio/speech" or any(k in mid_lower for k in ["tts", "voice"]):
                    capabilities.append("tts")
                
                if not capabilities:
                    continue
                
                capabilities = list(dict.fromkeys(capabilities))

                results.append(ModelInfo(
                    id=model_id,
                    name=name,
                    provider=self.provider_name,
                    capabilities=capabilities,
                    context_window=context_window,
                    input_cost_per_million=0.10,
                    output_cost_per_million=0.20,
                    supports_streaming=True,
                    supports_vision="vision" in mid_lower or "4o" in mid_lower
                ))

            def sort_key(m: ModelInfo):
                mid = m.id.lower()
                is_prio = any(p in mid for p in ["aion", "gpt-4", "claude", "llama", "qwen", "mistral"])
                return (not is_prio, mid)
            results.sort(key=sort_key)
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
                gender="neutral",
                description=f"CheaperInference voice: {v.capitalize()}"
            )
            for v in CHEAPER_INFERENCE_VOICES
        ]

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
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
        if is_voice and any(r in model.lower() for r in ["o1", "o3", "r1", "reasoning", "deepseek-r1"]):
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
