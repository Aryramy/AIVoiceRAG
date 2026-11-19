from fastapi import APIRouter
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.conversations import router as conversations_router
from backend.app.api.routes.knowledge import router as knowledge_router
from backend.app.api.routes.providers import router as providers_router
from backend.app.api.routes.settings import router as settings_router
from backend.app.api.routes.analytics import router as analytics_router
from backend.app.api.routes.voice import router as voice_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health_router)
api_router.include_router(conversations_router)
api_router.include_router(knowledge_router)
api_router.include_router(providers_router)
api_router.include_router(settings_router)
api_router.include_router(analytics_router)
api_router.include_router(voice_router)
