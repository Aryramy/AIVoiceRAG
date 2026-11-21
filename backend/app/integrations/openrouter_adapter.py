import time
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

OPENROUTER_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

class OpenRouterAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1").rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0), limits=limits)
        return self._client
    @property
    def provider_name(self) -> str:
        return "openrouter"

    def _headers(self, override_key: Optional[str] = None) -> Dict[str, str]:
        key = override_key or self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://voicerag.local",
            "X-Title": "VoiceRag Platform",
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
                message="OpenRouter API key is missing or not configured.",
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
                        message=f"Connected successfully. Discovered {len(models)} live models.",
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
                context_length = m.get("context_length", 8192)
                pricing = m.get("pricing", {})
                prompt_per_token = float(pricing.get("prompt", 0) or 0)
                completion_per_token = float(pricing.get("completion", 0) or 0)
                in_cost_1m = round(prompt_per_token * 1_000_000, 4)
                out_cost_1m = round(completion_per_token * 1_000_000, 4)
                
                arch = m.get("architecture", {})
                modality = ""
                if isinstance(arch, dict):
                    modality = str(arch.get("modality", "")).lower()
                else:
                    modality = str(arch).lower()
                mid_lower = model_id.lower()

                # Filter out embedding, moderation, and image-only models from LLM list
                is_non_llm = any(p in mid_lower for p in [
                    "embed", "minilm", "bge", "e5", "rerank", "tts", "whisper", 
                    "transcribe", "moderation", "image", "imagen", "dall-e", "flux", 
                    "stable-diffusion", "bark", "musicgen", "realtime"
                ])
                
                capabilities = []
                # STT models (strictly exclude TTS/speech models)
                if ("audio->text" in modality or "transcribe" in mid_lower or "whisper" in mid_lower) and not any(k in mid_lower for k in ["tts", "speech"]):
                    capabilities.append("stt")
                # Audio/TTS models
                if "->text+audio" in modality or "->audio" in modality or "...audio" in modality or "tts" in mid_lower:
                    capabilities.append("tts")
                # LLM models: only true chat models
                if ("->text" in modality or "text" in modality) and not is_non_llm:
                    capabilities.append("llm")
                    
                if not capabilities:
                    continue
                    
                capabilities = list(dict.fromkeys(capabilities))
                supports_vis = ("image" in modality or "vision" in mid_lower or "vision" in str(m.get("description", "")).lower())
                
                results.append(ModelInfo(
                    id=model_id,
                    name=name,
                    provider=self.provider_name,
                    capabilities=capabilities,
                    context_window=context_length,
                    input_cost_per_million=in_cost_1m,
                    output_cost_per_million=out_cost_1m,
                    supports_streaming=True,
                    supports_vision=supports_vis,
                    description=m.get("description", "")
                ))
            
            def sort_key(m: ModelInfo):
                mid = m.id.lower()
                is_prio = any(p in mid for p in ["gpt-4", "claude-3", "gemini-2", "gemini-1.5", "llama-3", "qwen", "mistral"])
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
                gender="neutral" if v in ["alloy", "fable"] else ("male" if v in ["echo", "onyx"] else "female"),
                description=f"OpenRouter Native Voice: {v.capitalize()}"
            )
            for v in OPENROUTER_VOICES
        ]

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o-mini",
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
        # 1. Attempt standard /audio/transcriptions endpoint
        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": "openai/whisper-large-v3"}
        if language and language.strip().lower() not in ["auto", "multilingual", "none"]:
            data["language"] = language.strip().lower()
        files = {"file": (filename, audio_bytes, "audio/wav")}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(url, headers=headers, data=data, files=files)
                if res.status_code == 200:
                    return res.json().get("text", "")
        except Exception:
            pass

        # 2. Multimodal chat completion transcription fallback
        import base64
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        chat_url = f"{self.base_url}/chat/completions"
        prompt = (
            "Transcribe the spoken audio verbatim in its original language and script "
            "(write Arabic in Arabic script and English in English). "
            "Do not translate, summarize, or add commentary."
        )
        if language and language.strip().lower() not in ["auto", "multilingual", "none"]:
            prompt += f" The spoken language is {language.strip()}."

        payload = {
            "model": "openai/gpt-4o-audio-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "input_audio", "input_audio": {"data": b64_audio, "format": "wav"}}
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(chat_url, headers=self._headers(), json=payload)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"].get("content", "").strip()

    async def synthesize_speech(self, text: str, voice: str = "alloy", model: str = "openai/gpt-audio") -> bytes:
        """
        OpenRouter Native TTS via chat/completions with modalities: ['text', 'audio']
        and audio: {'voice': voice, 'format': 'pcm16', 'stream': True}.
        Encodes streamed PCM16 chunks into a standard WAV container.
        """
        import base64
        import json
        import wave
        import io

        url = f"{self.base_url}/chat/completions"
        audio_model = model if ("audio" in model) else "openai/gpt-audio"
        payload = {
            "model": audio_model,
            "modalities": ["text", "audio"],
            "audio": {"voice": voice or "alloy", "format": "pcm16"},
            "stream": True,
            "messages": [
                {"role": "user", "content": f"Repeat the following text aloud verbatim:\n\n{text}"}
            ]
        }
        client = self._get_http_client()
        raw_pcm = bytearray()

        async with client.stream("POST", url, headers=self._headers(), json=payload, timeout=45.0) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        audio_dict = delta.get("audio", {})
                        if isinstance(audio_dict, dict) and "data" in audio_dict:
                            raw_pcm.extend(base64.b64decode(audio_dict["data"]))
                    except Exception:
                        continue

        if not raw_pcm:
            raise ValueError(f"No audio data returned by OpenRouter model '{audio_model}'")

        # Package raw 24kHz 16-bit mono PCM into standard playable WAV format
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(raw_pcm)
        return wav_io.getvalue()

    async def stream_synthesize(self, text: str, voice: str = "alloy", model: str = "openai/gpt-audio") -> AsyncIterator[bytes]:
        audio_bytes = await self.synthesize_speech(text=text, voice=voice, model=model)
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]
