import time
import base64
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.integrations.base import BaseProviderAdapter
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult
from backend.app.core.config import settings

GEMINI_STUDIO_VOICES = [
    "Puck", "Charon", "Kore", "Fenrir", "Aoede", "Enceladus", "Iapetus", "Algieba",
    "Algenib", "Castor", "Pollux", "Vega", "Sirius", "Rigel", "Capella", "Procyon",
    "Altair", "Deneb", "Arcturus", "Betelgeuse", "Antares", "Spica", "Aldebaran",
    "Regulus", "Canopus", "Achernar", "Hadar", "Acrux", "Mimosa", "Gacrux"
]

class GeminiAdapter(BaseProviderAdapter):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=60.0)
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0), limits=limits)
        return self._client
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
                    mid_lower = model_id.lower()
                    
                    if "generateContent" not in supported_methods:
                        continue
                    
                    capabilities = []
                    # TTS models: models with "tts" or speech capability
                    if "tts" in mid_lower or "speech" in mid_lower:
                        capabilities.append("tts")
                    
                    # STT models: multimodal audio transcription models (strictly exclude TTS/speech models)
                    is_tts_or_speech = any(k in mid_lower for k in ["tts", "speech"])
                    if any(k in mid_lower for k in ["2.5-flash", "flash-latest", "3-flash", "flash", "2.0-flash", "1.5-flash", "transcribe"]) and not any(k in mid_lower for k in ["image", "imagen"]) and not is_tts_or_speech:
                        capabilities.append("stt")
                    
                    # LLM models: generateContent supported and not tts/image/embedding/robotics specific
                    is_aux = any(k in mid_lower for k in ["image", "imagen", "tts", "speech", "transcribe", "embed", "robotics", "aqa", "realtime", "decision"])
                    if not is_aux:
                        capabilities.append("llm")

                    if not capabilities:
                        continue

                    capabilities = list(dict.fromkeys(capabilities))

                    if "flash" in mid_lower:
                        in_cost = 0.075
                        out_cost = 0.30
                    elif "pro" in mid_lower:
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
                
                results.sort(key=lambda x: (not ("flash-latest" in x.id or "3.5-flash" in x.id), not "flash" in x.id, x.name))
                return results
        except Exception:
            return []

    async def list_voices(self) -> List[VoiceInfo]:
        return [
            VoiceInfo(
                id=v.lower(),
                name=f"Gemini {v}",
                provider=self.provider_name,
                language="multilingual",
                gender="neutral",
                description=f"Gemini Studio Voice: {v}"
            )
            for v in GEMINI_STUDIO_VOICES
        ]

    async def chat_complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-flash-latest",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        is_voice: bool = False,
        **kwargs: Any
    ) -> Any:
        clean_model = model.replace("models/", "")
        # Route voice or deprecated models to fast active flash tier
        if is_voice:
            if clean_model in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-pro-latest"):
                clean_model = "gemini-3.5-flash"

        gen_config: Dict[str, Any] = {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        }
        if is_voice:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}

        contents = []
        system_instruction = None
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_instruction = {"parts": [{"text": content}]}
            elif role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role in ("assistant", "model"):
                contents.append({"role": "model", "parts": [{"text": content}]})

        native_payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": gen_config
        }
        if system_instruction:
            native_payload["system_instruction"] = system_instruction

        client = self._get_http_client()
        if not stream:
            url = f"{self.base_url}/models/{clean_model}:generateContent?key={self.api_key}"
            res = await client.post(url, json=native_payload, timeout=60.0)
            res.raise_for_status()
            data = res.json()
            reply_text = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    reply_text = parts[0].get("text", "")
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": reply_text}
                }]
            }
        else:
            url = f"{self.base_url}/models/{clean_model}:streamGenerateContent?alt=sse&key={self.api_key}"
            async def stream_generator():
                async with client.stream("POST", url, json=native_payload, timeout=60.0) as response:
                    response.raise_for_status()
                    import json
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if not data_str:
                                continue
                            try:
                                chunk = json.loads(data_str)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        t = p.get("text", "")
                                        if t:
                                            yield t
                            except Exception:
                                continue
            return stream_generator()

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language: Optional[str] = None) -> str:
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
        mime_type = "audio/wav"
        if filename.endswith(".mp3"):
            mime_type = "audio/mp3"
        elif filename.endswith(".ogg"):
            mime_type = "audio/ogg"
        elif filename.endswith(".webm"):
            mime_type = "audio/webm"

        model = "gemini-flash-latest"
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        
        prompt = (
            "Transcribe the spoken audio verbatim in its original language and script "
            "(write Arabic in Arabic script and English in English). "
            "Do not translate, summarize, or add commentary."
        )
        if language and language.strip().lower() not in ["auto", "multilingual", "none"]:
            prompt += f" The spoken language is {language.strip()}."

        payload = {
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": mime_type, "data": b64_audio}},
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "thinkingConfig": {"thinkingBudget": 0},
                "temperature": 0.0
            }
        }

        client = self._get_http_client()
        res = await client.post(url, json=payload)
        res.raise_for_status()

        data = res.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return ""
    async def synthesize_speech(self, text: str, voice: str = "Puck", model: str = "gemini-2.5-flash-preview-tts") -> bytes:
        import wave
        import io
        voice_name = voice.capitalize()
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        # Gemini TTS requires clear directive to synthesize speech from text rather than generate conversation
        tts_prompt = f"Read the following text aloud:\n{text}"
        payload = {
            "contents": [{
                "parts": [{"text": tts_prompt}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name
                        }
                    }
                }
            }
        }
        client = self._get_http_client()
        res = await client.post(url, json=payload)
        res.raise_for_status()

        data = res.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for p in parts:
                if "inlineData" in p:
                    audio_b64 = p["inlineData"].get("data", "")
                    raw_audio = base64.b64decode(audio_b64)
                    
                    # Gemini TTS returns raw audio/L16;codec=pcm;rate=24000.
                    # If not already wrapped in RIFF or MP3 header, encapsulate in valid 24kHz 16-bit mono RIFF WAV
                    if not raw_audio.startswith(b"RIFF") and not (raw_audio.startswith(b"ID3") or raw_audio[:2] == b"\xff\xfb"):
                        wav_io = io.BytesIO()
                        with wave.open(wav_io, "wb") as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)
                            wav_file.setframerate(24000)
                            wav_file.writeframes(raw_audio)
                        return wav_io.getvalue()
                    return raw_audio
        raise ValueError("No audio content returned by Gemini speech synthesis")

    async def stream_synthesize(self, text: str, voice: str = "Puck", model: str = "gemini-2.5-flash-preview-tts") -> AsyncIterator[bytes]:
        audio_bytes = await self.synthesize_speech(text=text, voice=voice, model=model)
        chunk_size = 4096
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i:i + chunk_size]
