# Multi-Agent Coordination Specification — VoiceRag

## 1. Orchestration Model
VoiceRag development is coordinated under an autonomous lead orchestrator managing specialized functional roles across frontend, backend, RAG engineering, voice AI, and QA automation.

## 2. Specialized Roles & Responsibilities

### 2.1 Lead Architect & Orchestrator
- Global system integrity, service boundary enforcement, dependency management, and phase milestone gates.

### 2.2 Backend & Data Engineer
- FastAPI modular REST endpoints, SQLite WAL database, SQLAlchemy 2.0 schemas, Alembic migrations, and security middleware.

### 2.3 RAG & Retrieval Specialist
- Multi-format ingestion (PDF, DOCX, XLSX, TXT, MD), structure-aware chunking, FastEmbed multilingual vectors, Qdrant indexing, BM25Okapi sparse search, Reciprocal Rank Fusion (RRF), cross-encoder reranking, and citation generation.

### 2.4 Voice AI & Realtime Engineer
- LiveKit WebRTC token issuance, Silero VAD integration, streaming STT/TTS pipeline, Arabic/English voice selection, and barge-in / interruption handling.

### 2.5 Provider & Router Engineer
- Dynamic model discovery from live provider endpoints (OpenAI, Gemini, OpenRouter, CheaperInference), capability mapping, Smart Auto Router policy engine, and centralized pricing telemetry.

### 2.6 Frontend UI/UX Designer & Engineer
- Next.js 15, TypeScript, Tailwind CSS, UI/UX Pro Max design intelligence, 3-area layout, responsive layouts, theme switching (Light/Dark/System), and Arabic Right-to-Left (RTL) mirroring.

### 2.7 QA Automation & Quality Engineer
- Pytest backend test suites, Vitest frontend tests, Playwright browser journeys, and multilingual evaluation benchmarks.

