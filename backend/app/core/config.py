import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "VoiceRag"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "voicerag-super-secret-key-32-chars-minimum-prod")
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/voicerag.db")
    
    # Qdrant Vector Storage
    QDRANT_STORAGE_PATH: str = os.getenv("QDRANT_STORAGE_PATH", "./data/qdrant")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "voicerag_knowledge")
    
    # Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")

    # Provider API Keys & Base URLs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_BASE_URL: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    CHEAPER_INFERENCE_API_KEY: str = os.getenv("CHEAPER_INFERENCE_API_KEY", "")
    CHEAPER_INFERENCE_BASE_URL: str = os.getenv("CHEAPER_INFERENCE_BASE_URL", "https://api.cheaperinference.com/v1")

    # LiveKit WebRTC
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "ws://127.0.0.1:7880")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "devkey")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "secret")

    # Defaults
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "openrouter")
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "google/gemini-2.5-flash")
    DEFAULT_STT_PROVIDER: str = os.getenv("DEFAULT_STT_PROVIDER", "openai")
    DEFAULT_STT_MODEL: str = os.getenv("DEFAULT_STT_MODEL", "whisper-1")
    DEFAULT_TTS_PROVIDER: str = os.getenv("DEFAULT_TTS_PROVIDER", "openai")
    DEFAULT_TTS_MODEL: str = os.getenv("DEFAULT_TTS_MODEL", "tts-1")
    DEFAULT_VOICE: str = os.getenv("DEFAULT_VOICE", "alloy")
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "auto")

    # RAG Settings
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "5"))
    ABSTENTION_THRESHOLD: float = float(os.getenv("ABSTENTION_THRESHOLD", "0.35"))

    class Config:
        case_sensitive = True

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.QDRANT_STORAGE_PATH, exist_ok=True)
os.makedirs("./data", exist_ok=True)
