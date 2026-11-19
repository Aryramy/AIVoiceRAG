from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.app.core.config import settings
from backend.app.database import init_db
from backend.app.api.routes import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB tables and defaults are initialized
    init_db()
    os.makedirs(os.path.join(settings.BASE_DIR, "data", "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.BASE_DIR, "data", "qdrant"), exist_ok=True)
    yield
    # Shutdown logic if needed

app = FastAPI(
    title="VoiceRag API",
    description="Enterprise Multilingual AI Voice & Knowledge Assistant Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include All API v1 routes
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "service": "VoiceRag API",
        "description": "Enterprise Multilingual AI Voice & Knowledge Platform (English + Arabic)",
        "docs_url": "/docs",
        "health_check": "/api/v1/health",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
