from backend.app.core.database import engine, SessionLocal
from backend.app.database.models import Base, AISettings

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if default AI settings exist, if not create
        settings = db.query(AISettings).filter(AISettings.id == "default").first()
        if not settings:
            default_settings = AISettings(
                id="default",
                llm_provider="openai",
                llm_model="gpt-4o-mini",
                stt_provider="openai",
                stt_model="whisper-1",
                tts_provider="edge_tts",
                tts_voice_en="en-US-JennyNeural",
                tts_voice_ar="ar-SA-HamedNeural",
                voice_provider="openai",
                voice_model="gpt-4o-realtime-preview",
                routing_strategy="smart_auto"
            )
            db.add(default_settings)
            db.commit()
    finally:
        db.close()
