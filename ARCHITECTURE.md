# VoiceRag Architecture Summary

For comprehensive documentation, see [docs/SYSTEM_ARCHITECTURE.md](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/SYSTEM_ARCHITECTURE.md).

## Quick Reference
- **Backend**: FastAPI modular monolith in `backend/app/`.
- **Database**: SQLite WAL mode via SQLAlchemy 2.0.
- **Vector DB**: Qdrant embedded in `data/qdrant/`.
- **Frontend**: Next.js 15 + React + Tailwind + Lucide Icons in `frontend/`.
- **Real-Time Voice**: LiveKit WebRTC + Silero VAD + Edge-TTS / Provider TTS.
- **Provider Adapters**: OpenAI, Gemini, OpenRouter, CheaperInference in `backend/app/integrations/`.
