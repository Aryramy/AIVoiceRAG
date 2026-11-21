from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from backend.app.schemas.provider import ModelInfo, VoiceInfo, ProviderTestResult

class BaseProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def test_connection(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> ProviderTestResult:
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        pass

    @abstractmethod
    async def list_voices(self) -> List[VoiceInfo]:
        pass

    @abstractmethod
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
        pass

    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav", language: Optional[str] = None) -> str:
        raise NotImplementedError(f"STT is not supported by {self.provider_name}")

    async def synthesize_speech(self, text: str, voice: str = "alloy", model: Optional[str] = None) -> bytes:
        raise NotImplementedError(f"TTS is not supported by {self.provider_name}")

    async def stream_synthesize(self, text: str, voice: str = "alloy", model: Optional[str] = None) -> AsyncIterator[bytes]:
        raise NotImplementedError(f"Streaming TTS is not supported by {self.provider_name}")

