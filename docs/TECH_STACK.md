# VoiceRag — Technology Stack & Version Matrix

## 1. Backend Stack
- **Runtime**: Python 3.12.10 (AMD64 on Windows Server / Desktop)
- **API Framework**: FastAPI 0.115+ (Asynchronous, OpenAPI 3.1, Dependency Injection)
- **ASGI Server**: Uvicorn 0.34+ (uvloop/standard workers)
- **Database ORM**: SQLAlchemy 2.0+ (Declarative 2.0 syntax, Async/Sync Engine, SQLite WAL mode)
- **Database Migrations**: Alembic 1.14+
- **Vector Database**: Qdrant Client 1.12+ (Embedded local storage & remote cluster compatibility)
- **Hybrid Retrieval**:
  - Dense: FastEmbed 0.7+ (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`)
  - Sparse: `rank-bm25` (BM25Okapi implementation)
  - Fusion: Reciprocal Rank Fusion (RRF)
- **Document Extractors**:
  - PDF: `pypdf` 5.1+ & `pymupdf`
  - DOCX: `python-docx` 1.1+
  - Excel/CSV: `openpyxl` 3.1+ & Python `csv`
- **Voice AI & WebRTC**:
  - LiveKit WebRTC SDK (`livekit`, `livekit-api`, `livekit-agents`)
  - VAD: Silero VAD
  - Fallback Speech Synthesis: `edge-tts` (Arabic + English neural voices)
- **AI Provider Integrations**:
  - `openai` 1.55+ (OpenAI official SDK)
  - `google-genai` 0.1.1+ (Google Gemini official SDK)
  - `httpx` 0.28+ (Async HTTP client for OpenRouter & CheaperInference OpenAI-compatible endpoints)
  - `litellm` 1.50+ (Multi-provider unified gateway fallback)
- **Testing**: `pytest` 8.3+, `pytest-asyncio` 0.25+

## 2. Frontend Stack
- **Framework**: Next.js 15+ (App Router, Server & Client Components)
- **Language**: TypeScript 5.7+
- **UI & Styling**:
  - Tailwind CSS 3.4+ / 4.0+
  - UI/UX Pro Max Design System & Component Guidelines
  - Lucide React (SVG Iconography - strict no-emoji rule)
- **Realtime & Audio**:
  - Web Audio API (AnalyserNode, AudioWorklet, Canvas Waveform Visualizer)
  - LiveKit Client SDK (`livekit-client`)
- **Internationalization & Layout**:
  - Native RTL direction switching (`dir="rtl"`, `dir="ltr"`)
  - Direction-aware CSS classes (`rtl:...`, `start`, `end`)
  - Arabic typography (Cairo / IBM Plex Sans Arabic / Noto Sans Arabic)
