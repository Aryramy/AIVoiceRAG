import io
import edge_tts
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.schemas.provider import VoiceInfo

_VOICES_CACHE: Optional[List[VoiceInfo]] = None

class EdgeTTSAdapter:
    def __init__(self):
        pass

    @property
    def provider_name(self) -> str:
        return "edge_tts"

    async def list_voices(self) -> List[VoiceInfo]:
        global _VOICES_CACHE
        if _VOICES_CACHE is not None and len(_VOICES_CACHE) > 0:
            return _VOICES_CACHE

        try:
            raw_voices = await edge_tts.list_voices()
            filtered: List[VoiceInfo] = []
            for v in raw_voices:
                locale = v.get("Locale", "").lower()
                if locale.startswith("en") or locale.startswith("ar"):
                    gender = v.get("Gender", "neutral").lower()
                    friendly = v.get("FriendlyName", v.get("ShortName", ""))
                    short = v.get("ShortName", "")
                    lang = "ar" if locale.startswith("ar") else "en"
                    filtered.append(VoiceInfo(
                        id=short,
                        name=f"{friendly}",
                        provider=self.provider_name,
                        language=lang,
                        gender=gender,
                        description=v.get("LocaleName", "")
                    ))
            if filtered:
                _VOICES_CACHE = filtered
                return filtered
        except Exception:
            pass

        return self._fallback_voices()

    def list_voices_sync(self) -> List[VoiceInfo]:
        global _VOICES_CACHE
        if _VOICES_CACHE:
            return _VOICES_CACHE
        return self._fallback_voices()

    def _fallback_voices(self) -> List[VoiceInfo]:
        return [
            # Arabic Voices
            VoiceInfo(id="ar-SA-HamedNeural", name="Microsoft Hamed Online (Natural) - Arabic (Saudi Arabia)", provider=self.provider_name, language="ar", gender="male", description="Arabic (Saudi Arabia)"),
            VoiceInfo(id="ar-SA-ZariyahNeural", name="Microsoft Zariyah Online (Natural) - Arabic (Saudi Arabia)", provider=self.provider_name, language="ar", gender="female", description="Arabic (Saudi Arabia)"),
            VoiceInfo(id="ar-EG-SalmaNeural", name="Microsoft Salma Online (Natural) - Arabic (Egypt)", provider=self.provider_name, language="ar", gender="female", description="Arabic (Egypt)"),
            VoiceInfo(id="ar-EG-ShakirNeural", name="Microsoft Shakir Online (Natural) - Arabic (Egypt)", provider=self.provider_name, language="ar", gender="male", description="Arabic (Egypt)"),
            VoiceInfo(id="ar-AE-FatimaNeural", name="Microsoft Fatima Online (Natural) - Arabic (UAE)", provider=self.provider_name, language="ar", gender="female", description="Arabic (UAE)"),
            # English Voices
            VoiceInfo(id="en-US-JennyNeural", name="Microsoft Jenny Online (Natural) - English (United States)", provider=self.provider_name, language="en", gender="female", description="English (United States)"),
            VoiceInfo(id="en-US-GuyNeural", name="Microsoft Guy Online (Natural) - English (United States)", provider=self.provider_name, language="en", gender="male", description="English (United States)"),
            VoiceInfo(id="en-US-AriaNeural", name="Microsoft Aria Online (Natural) - English (United States)", provider=self.provider_name, language="en", gender="female", description="English (United States)"),
            VoiceInfo(id="en-GB-SoniaNeural", name="Microsoft Sonia Online (Natural) - English (United Kingdom)", provider=self.provider_name, language="en", gender="female", description="English (United Kingdom)"),
            VoiceInfo(id="en-GB-RyanNeural", name="Microsoft Ryan Online (Natural) - English (United Kingdom)", provider=self.provider_name, language="en", gender="male", description="English (United Kingdom)"),
        ]

    async def synthesize(self, text: str, voice: str = "en-US-JennyNeural") -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        mp3_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buffer.write(chunk["data"])
        return mp3_buffer.getvalue()

    async def stream_synthesize(self, text: str, voice: str = "en-US-JennyNeural") -> AsyncIterator[bytes]:
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

_EDGE_ADAPTER = EdgeTTSAdapter()

def get_edge_tts_adapter() -> EdgeTTSAdapter:
    return _EDGE_ADAPTER

