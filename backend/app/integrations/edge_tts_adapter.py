import io
import edge_tts
from typing import List, Dict, Any, Optional
from backend.app.schemas.provider import VoiceInfo

class EdgeTTSAdapter:
    def __init__(self):
        pass

    @property
    def provider_name(self) -> str:
        return "edge_tts"

    def list_voices(self) -> List[VoiceInfo]:
        return [
            # Arabic Voices
            VoiceInfo(
                id="ar-SA-HamedNeural",
                name="Hamed (Saudi Arabia)",
                provider=self.provider_name,
                language="ar",
                gender="male",
                description="Natural, formal Arabic (Saudi dialect & MSA)"
            ),
            VoiceInfo(
                id="ar-SA-ZariyahNeural",
                name="Zariyah (Saudi Arabia)",
                provider=self.provider_name,
                language="ar",
                gender="female",
                description="Warm, clear Arabic (Saudi dialect & MSA)"
            ),
            VoiceInfo(
                id="ar-EG-SalmaNeural",
                name="Salma (Egypt)",
                provider=self.provider_name,
                language="ar",
                gender="female",
                description="Clear, expressive Egyptian Arabic & MSA"
            ),
            VoiceInfo(
                id="ar-EG-ShakirNeural",
                name="Shakir (Egypt)",
                provider=self.provider_name,
                language="ar",
                gender="male",
                description="Professional, deep Egyptian Arabic & MSA"
            ),
            VoiceInfo(
                id="ar-AE-FatimaNeural",
                name="Fatima (UAE)",
                provider=self.provider_name,
                language="ar",
                gender="female",
                description="Polished Emirati Arabic & MSA"
            ),
            # English Voices
            VoiceInfo(
                id="en-US-JennyNeural",
                name="Jenny (US)",
                provider=self.provider_name,
                language="en",
                gender="female",
                description="Crisp, professional American English"
            ),
            VoiceInfo(
                id="en-US-GuyNeural",
                name="Guy (US)",
                provider=self.provider_name,
                language="en",
                gender="male",
                description="Casual, friendly American English"
            ),
            VoiceInfo(
                id="en-US-AriaNeural",
                name="Aria (US)",
                provider=self.provider_name,
                language="en",
                gender="female",
                description="Versatile, expressive American English"
            ),
            VoiceInfo(
                id="en-GB-SoniaNeural",
                name="Sonia (UK)",
                provider=self.provider_name,
                language="en",
                gender="female",
                description="Refined British English"
            ),
            VoiceInfo(
                id="en-GB-RyanNeural",
                name="Ryan (UK)",
                provider=self.provider_name,
                language="en",
                gender="male",
                description="Warm British English"
            ),
        ]

    async def synthesize(self, text: str, voice: str = "en-US-JennyNeural") -> bytes:
        communicate = edge_tts.Communicate(text, voice)
        mp3_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buffer.write(chunk["data"])
        return mp3_buffer.getvalue()
