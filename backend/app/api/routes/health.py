import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.database import get_db
from backend.app.services.retrieval import get_retrieval_service
from backend.app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def health_check(db: Session = Depends(get_db)):
    # Verify Database connectivity
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Verify Vector Database
    retrieval_svc = get_retrieval_service()
    vector_ok = False
    try:
        collections = retrieval_svc.qdrant.get_collections()
        vector_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if db_ok and vector_ok else "degraded",
        "service": "VoiceRag API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
        "components": {
            "database": "connected" if db_ok else "error",
            "vector_store": "connected" if vector_ok else "error"
        }
    }
