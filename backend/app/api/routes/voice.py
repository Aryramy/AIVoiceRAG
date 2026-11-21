import time
import re
from typing import Optional, Tuple, AsyncIterator
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.database.models import AISettings, UsageLog
from backend.app.integrations import get_provider_adapter, get_edge_tts_adapter
from backend.app.integrations.openai_adapter import OPENAI_NATIVE_VOICES
from backend.app.integrations.gemini_adapter import GEMINI_STUDIO_VOICES
from backend.app.integrations.cheaper_inference_adapter import CHEAPER_INFERENCE_VOICES
from backend.app.integrations.openrouter_adapter import OPENROUTER_VOICES
from backend.app.services.pricing import get_pricing_calculator

router = APIRouter(prefix="/voice", tags=["Voice"])

def clean_voice_text(text: str) -> str:
    """
    Strips inline citation brackets (e.g., [1], [2], [1][2], [1, 2], [1-3]),
    residual markdown (*, #, _, `, ~, >), and markdown links before TTS
    so citation numbers and symbols are never spoken aloud.
    """
    if not text:
        return ""
    # 1. Strip markdown links [label](url) -> label
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # 2. Strip citation markers [1], [2], [1, 2], [1][2], [1-3], [1]-[3]
    cleaned = re.sub(r'\[\s*\d+(?:\s*[,-]\s*\d+)*\s*\]', '', cleaned)
    # 3. Strip any residual citation brackets like [source 1] or [1.1]
    cleaned = re.sub(r'\[\s*(?:source\s*)?\d+(?:\.\d+)?\s*\]', '', cleaned, flags=re.IGNORECASE)
    # 4. Strip residual markdown formatting symbols: *, #, _, `, ~, >
    cleaned = re.sub(r'[*#_`~>]', '', cleaned)
    # 5. Fix spaces before punctuation after citation removal
    cleaned = re.sub(r'\s+([,.;:!?،۔])', r'\1', cleaned)
    # 6. Normalize whitespace
    return re.sub(r'\s+', ' ', cleaned).strip()

class SynthesizeRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None
    provider: Optional[str] = None

class LiveKitTokenRequest(BaseModel):
    room_name: str = "voicerag-room"
    participant_name: str = "user"

def resolve_tts_provider_and_voice(
    requested_provider: Optional[str],
    requested_voice: Optional[str],
    language: str,
    settings_record: Optional[AISettings],
    text: Optional[str] = None
) -> Tuple[str, str]:
    if text is not None and text.strip():
        is_ar = bool(re.search(r'[\u0600-\u06FF]', text))
    else:
        is_ar = language.lower().startswith("ar")
    target_configured_voice = (settings_record.tts_voice_ar if is_ar else settings_record.tts_voice_en) if settings_record else None

    # Handle language mismatch in requested_voice (e.g. caller passed an English voice for Arabic text or vice versa)
    raw_voice = requested_voice
    if not raw_voice:
        raw_voice = target_configured_voice
    elif is_ar and (raw_voice.startswith("en-") or (settings_record and settings_record.tts_voice_en and raw_voice.lower() == settings_record.tts_voice_en.lower())):
        raw_voice = target_configured_voice or "ar-SA-HamedNeural"
    elif not is_ar and (raw_voice.startswith("ar-") or (settings_record and settings_record.tts_voice_ar and raw_voice.lower() == settings_record.tts_voice_ar.lower())):
        raw_voice = target_configured_voice or "en-US-JennyNeural"

    # 1. Determine provider
    provider = (requested_provider or "").lower().strip()
    if not provider:
        # Check settings record primary TTS provider first
        if settings_record and settings_record.tts_provider:
            provider = settings_record.tts_provider.lower()
        elif raw_voice:
            v_lower = raw_voice.lower()
            if any(raw_voice.startswith(prefix) for prefix in ["ar-", "en-", "zh-", "fr-", "de-", "es-"]) or "-" in raw_voice:
                provider = "edge_tts"
            elif v_lower in [g.lower() for g in GEMINI_STUDIO_VOICES]:
                provider = "gemini"
            elif v_lower in [c.lower() for c in CHEAPER_INFERENCE_VOICES] and v_lower not in [o.lower() for o in OPENAI_NATIVE_VOICES]:
                provider = "cheaper_inference"
            else:
                provider = "openai"
        else:
            provider = "edge_tts"

    # 2. Select appropriate voice for the determined provider
    if provider == "gemini":
        gemini_ar = (target_configured_voice if (target_configured_voice and target_configured_voice.lower() in [g.lower() for g in GEMINI_STUDIO_VOICES]) else "Algieba")
        gemini_en = (target_configured_voice if (target_configured_voice and target_configured_voice.lower() in [g.lower() for g in GEMINI_STUDIO_VOICES]) else "Puck")
        fallback_v = gemini_ar if is_ar else gemini_en
        voice = raw_voice if (raw_voice and raw_voice.lower() in [g.lower() for g in GEMINI_STUDIO_VOICES]) else fallback_v
    elif provider == "cheaper_inference":
        voice = raw_voice if (raw_voice and raw_voice.lower() in [c.lower() for c in CHEAPER_INFERENCE_VOICES]) else (target_configured_voice or "alloy")
    elif provider == "openrouter":
        voice = raw_voice if (raw_voice and raw_voice.lower() in [o.lower() for o in OPENROUTER_VOICES]) else (target_configured_voice or "alloy")
    elif provider == "openai":
        voice = raw_voice if (raw_voice and raw_voice.lower() in [o.lower() for o in OPENAI_NATIVE_VOICES]) else (target_configured_voice or "alloy")
    else:
        provider = "edge_tts"
        if is_ar:
            voice = raw_voice if (raw_voice and raw_voice.startswith("ar-")) else (target_configured_voice if (target_configured_voice and target_configured_voice.startswith("ar-")) else "ar-SA-HamedNeural")
        else:
            voice = raw_voice if (raw_voice and not raw_voice.startswith("ar-") and "-" in raw_voice) else (target_configured_voice if (target_configured_voice and "-" in target_configured_voice and not target_configured_voice.startswith("ar-")) else "en-US-JennyNeural")

    return provider, voice

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
    allow_fallback: bool = Query(True),
    db: Session = Depends(get_db)
):
    start = time.perf_counter()
    audio_bytes = await file.read()
    
    settings_record = db.query(AISettings).first()
    stt_provider = (provider or (settings_record.stt_provider if settings_record else "openai")).lower()
    
    adapter = get_provider_adapter(stt_provider)
    if not adapter or not hasattr(adapter, "transcribe_audio"):
        if not allow_fallback:
            raise HTTPException(status_code=400, detail=f"Provider '{stt_provider}' does not support STT transcribe_audio.")
        # Fallback chain across supported providers
        for candidate in ["openai", "gemini", "cheaper_inference", "openrouter"]:
            candidate_adapter = get_provider_adapter(candidate)
            if candidate_adapter and hasattr(candidate_adapter, "transcribe_audio"):
                adapter = candidate_adapter
                stt_provider = candidate
                break

    if not adapter or not hasattr(adapter, "transcribe_audio"):
        raise HTTPException(status_code=500, detail="No suitable STT provider configured.")

    try:
        text = await adapter.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.wav",
            language=language
        )
        latency = round((time.perf_counter() - start) * 1000, 2)
        
        # Estimate audio duration roughly by file size (32KB/sec typical for WAV)
        duration_sec = max(1.0, len(audio_bytes) / 32000.0)
        pricing_calc = get_pricing_calculator()
        cost_usd = pricing_calc.calculate_stt_cost("whisper-1", duration_sec)

        usage = UsageLog(
            provider=stt_provider,
            model="transcribe",
            capability="stt",
            audio_seconds=duration_sec,
            cost_usd=cost_usd,
            latency_ms=latency,
            status="success"
        )
        db.add(usage)
        db.commit()

        return {
            "text": text,
            "language": language,
            "provider": stt_provider,
            "duration_seconds": round(duration_sec, 2),
            "latency_ms": latency,
            "cost_usd": cost_usd
        }
    except Exception as e:
        latency = round((time.perf_counter() - start) * 1000, 2)
        usage = UsageLog(
            provider=stt_provider,
            model="transcribe",
            capability="stt",
            latency_ms=latency,
            status="error",
            error_message=str(e)
        )
        db.add(usage)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/synthesize")
async def synthesize_speech(
    data: SynthesizeRequest,
    provider_query: Optional[str] = Query(None, alias="provider"),
    allow_fallback: bool = Query(True),
    db: Session = Depends(get_db)
):
    start = time.perf_counter()
    data.text = clean_voice_text(data.text)
    if not data.text:
        return Response(content=b"", media_type="audio/mpeg")

    settings_record = db.query(AISettings).first()
    
    provider, voice = resolve_tts_provider_and_voice(
        requested_provider=data.provider or provider_query,
        requested_voice=data.voice,
        language=data.language,
        settings_record=settings_record,
        text=data.text
    )

    is_ar_speech = bool(re.search(r'[\u0600-\u06FF]', data.text)) or data.language.lower().startswith("ar")

    try:
        if provider == "edge_tts":
            edge = get_edge_tts_adapter()
            audio_bytes = await edge.synthesize(text=data.text, voice=voice)
        else:
            adapter = get_provider_adapter(provider)
            if adapter and hasattr(adapter, "synthesize_speech"):
                audio_bytes = await adapter.synthesize_speech(text=data.text, voice=voice)
            else:
                edge = get_edge_tts_adapter()
                audio_bytes = await edge.synthesize(text=data.text, voice="ar-SA-HamedNeural" if is_ar_speech else "en-US-JennyNeural")
                provider = "edge_tts"

        latency = round((time.perf_counter() - start) * 1000, 2)
        pricing_calc = get_pricing_calculator()
        cost_usd = pricing_calc.calculate_tts_cost(provider, voice, len(data.text))

        usage = UsageLog(
            provider=provider,
            model=voice,
            capability="tts",
            cost_usd=cost_usd,
            latency_ms=latency,
            status="success"
        )
        db.add(usage)
        db.commit()

        media_type = "audio/wav" if (audio_bytes and audio_bytes.startswith(b"RIFF")) else "audio/mpeg"
        return Response(content=audio_bytes, media_type=media_type)

    except Exception as e:
        if not allow_fallback:
            raise HTTPException(status_code=500, detail=f"Speech synthesis failed for provider '{provider}': {str(e)}")
        # Fallback to Edge TTS if custom provider failed
        if provider != "edge_tts":
            try:
                edge = get_edge_tts_adapter()
                fb_voice = "ar-SA-HamedNeural" if data.language.lower().startswith("ar") else "en-US-JennyNeural"
                audio_bytes = await edge.synthesize(text=data.text, voice=fb_voice)
                media_type = "audio/wav" if (audio_bytes and audio_bytes.startswith(b"RIFF")) else "audio/mpeg"
                return Response(content=audio_bytes, media_type=media_type)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

@router.post("/synthesize/stream")
async def synthesize_speech_stream(
    data: SynthesizeRequest,
    provider_query: Optional[str] = Query(None, alias="provider"),
    allow_fallback: bool = Query(True),
    db: Session = Depends(get_db)
):
    """
    Streams audio chunks via HTTP chunked transfer as they are synthesized,
    lowering Time-To-First-Audio (TTFA) to under 300ms.
    """
    data.text = clean_voice_text(data.text)
    if not data.text:
        async def empty_generator():
            yield b""
        return StreamingResponse(empty_generator(), media_type="audio/mpeg")

    settings_record = db.query(AISettings).first()
    provider, voice = resolve_tts_provider_and_voice(
        requested_provider=data.provider or provider_query,
        requested_voice=data.voice,
        language=data.language,
        settings_record=settings_record,
        text=data.text
    )

    is_ar_speech = bool(re.search(r'[\u0600-\u06FF]', data.text)) or data.language.lower().startswith("ar")
    edge_fallback_voice = settings_record.tts_voice_ar if (is_ar_speech and settings_record and settings_record.tts_voice_ar and settings_record.tts_voice_ar.startswith("ar-")) else ("ar-SA-HamedNeural" if is_ar_speech else "en-US-JennyNeural")

    stream_headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

    try:
        if provider == "edge_tts":
            edge = get_edge_tts_adapter()
            return StreamingResponse(
                edge.stream_synthesize(text=data.text, voice=voice),
                media_type="audio/mpeg",
                headers=stream_headers
            )
        else:
            adapter = get_provider_adapter(provider)
            media_type = "audio/wav" if provider in ["gemini", "openrouter"] else "audio/mpeg"
            if adapter and hasattr(adapter, "stream_synthesize"):
                return StreamingResponse(
                    adapter.stream_synthesize(text=data.text, voice=voice),
                    media_type=media_type,
                    headers=stream_headers
                )
            elif adapter and hasattr(adapter, "synthesize_speech"):
                audio_bytes = await adapter.synthesize_speech(text=data.text, voice=voice)
                if audio_bytes and audio_bytes.startswith(b"RIFF"):
                    media_type = "audio/wav"
                async def byte_generator():
                    chunk_size = 4096
                    for i in range(0, len(audio_bytes), chunk_size):
                        yield audio_bytes[i:i + chunk_size]
                return StreamingResponse(byte_generator(), media_type=media_type, headers=stream_headers)
            else:
                edge = get_edge_tts_adapter()
                return StreamingResponse(
                    edge.stream_synthesize(text=data.text, voice=edge_fallback_voice),
                    media_type="audio/mpeg",
                    headers=stream_headers
                )
    except Exception as e:
        if not allow_fallback:
            raise HTTPException(status_code=500, detail=f"Speech streaming failed for provider '{provider}': {str(e)}")
        # Fallback to Edge TTS streaming
        try:
            edge = get_edge_tts_adapter()
            return StreamingResponse(
                edge.stream_synthesize(text=data.text, voice=edge_fallback_voice),
                media_type="audio/mpeg",
                headers=stream_headers
            )
        except Exception:
            raise HTTPException(status_code=500, detail=f"Speech streaming failed: {str(e)}")

@router.post("/livekit-token")
def generate_livekit_token(data: LiveKitTokenRequest):
    """
    Generates a WebRTC connection token for LiveKit real-time voice sessions.
    """
    try:
        from livekit.api import AccessToken, VideoGrants

        token = (
            AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            .with_identity(data.participant_name)
            .with_name(data.participant_name)
            .with_grants(VideoGrants(
                room_join=True,
                room=data.room_name,
                can_publish=True,
                can_subscribe=True
            ))
            .to_jwt()
        )
        return {
            "token": token,
            "url": settings.LIVEKIT_URL,
            "room_name": data.room_name,
            "participant_name": data.participant_name
        }
    except Exception as e:
        # Fallback raw JWT signing if native livekit-api protocol fails
        import jwt
        payload = {
            "iss": settings.LIVEKIT_API_KEY,
            "sub": data.participant_name,
            "name": data.participant_name,
            "video": {
                "roomJoin": True,
                "room": data.room_name,
                "canPublish": True,
                "canSubscribe": True
            },
            "exp": int(time.time()) + 3600
        }
        raw_token = jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")
        return {
            "token": raw_token,
            "url": settings.LIVEKIT_URL,
            "room_name": data.room_name,
            "participant_name": data.participant_name
        }
