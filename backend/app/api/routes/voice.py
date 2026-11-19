import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.database.models import AISettings, UsageLog
from backend.app.integrations import get_provider_adapter, get_edge_tts_adapter
from backend.app.services.pricing import get_pricing_calculator

router = APIRouter(prefix="/voice", tags=["Voice"])

class SynthesizeRequest(BaseModel):
    text: str
    language: str = "en"
    voice: Optional[str] = None
    provider: Optional[str] = None

class LiveKitTokenRequest(BaseModel):
    room_name: str = "voicerag-room"
    participant_name: str = "user"

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    start = time.perf_counter()
    audio_bytes = await file.read()
    
    settings_record = db.query(AISettings).first()
    stt_provider = settings_record.stt_provider if settings_record else "openai"
    
    adapter = get_provider_adapter(stt_provider)
    if not adapter or not hasattr(adapter, "transcribe_audio"):
        # Fallback to OpenAI if configured
        adapter = get_provider_adapter("openai")

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
            model="whisper-1",
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
            "duration_seconds": round(duration_sec, 2),
            "latency_ms": latency,
            "cost_usd": cost_usd
        }
    except Exception as e:
        latency = round((time.perf_counter() - start) * 1000, 2)
        usage = UsageLog(
            provider=stt_provider,
            model="whisper-1",
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
    db: Session = Depends(get_db)
):
    start = time.perf_counter()
    settings_record = db.query(AISettings).first()
    
    provider = data.provider or (settings_record.tts_provider if settings_record else "edge_tts")
    is_ar = data.language.lower().startswith("ar")
    
    # Choose default voice based on language if not specified
    if not data.voice:
        if settings_record:
            voice = settings_record.tts_voice_ar if is_ar else settings_record.tts_voice_en
        else:
            voice = "ar-SA-HamedNeural" if is_ar else "en-US-JennyNeural"
    else:
        voice = data.voice

    try:
        if provider == "openai":
            adapter = get_provider_adapter("openai")
            if adapter and hasattr(adapter, "synthesize_speech"):
                audio_bytes = await adapter.synthesize_speech(text=data.text, voice=voice)
            else:
                edge = get_edge_tts_adapter()
                audio_bytes = await edge.synthesize(text=data.text, voice="en-US-JennyNeural")
        else:
            edge = get_edge_tts_adapter()
            audio_bytes = await edge.synthesize(text=data.text, voice=voice)

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

        return Response(content=audio_bytes, media_type="audio/mpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

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

