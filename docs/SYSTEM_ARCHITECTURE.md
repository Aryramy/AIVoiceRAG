# VoiceRag — System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Presentation Tier (Next.js 15 / React / Tailwind)"]
        UI["Main Workspace (Chat & Contextual Panel)"]
        AudioClient["WebRTC Voice Client (LiveKit SDK / AudioContext)"]
        SettingsUI["Unified AI Config & Admin Dashboard"]
    end

    subgraph Gateway ["API & Realtime Gateway Tier"]
        FastAPI["FastAPI 0.115+ REST / WebSocket Server"]
        AuthMiddleware["Security & Auth Middleware (JWT / RBAC)"]
        RateLimiter["Rate Limiting & Input Validation"]
    end

    subgraph IntentManagement ["Turn & Intent Management"]
        TurnManager["Turn Manager & Noise Filter"]
        IntentClassifier["Intent Classifier (Greeting / Knowledge / Ambient)"]
    end

    subgraph RAGEngine ["Hybrid RAG Engine"]
        DocIngest["Doc Ingestion (PDF / DOCX / XLSX / TXT / MD)"]
        Chunker["Structure-Aware Chunker"]
        Embedder["Multilingual Embedding (FastEmbed / sentence-transformers)"]
        Qdrant["Qdrant Vector Database (Dense Search)"]
        BM25["BM25 Keyword Index (Sparse Search)"]
        RRF["Reciprocal Rank Fusion (Hybrid)"]
        Reranker["Cross-Encoder Reranker"]
        CitationGen["Grounded Citation & Verifier"]
    end

    subgraph ProviderLayer ["Unified Provider & Routing Layer"]
        Router["Smart Auto Router (Cost / Quality / Latency)"]
        Registry["Provider Capability & Model Registry"]
        Discovery["Dynamic Model & Voice Discovery"]
        OpenAIAdapter["OpenAI Adapter"]
        GeminiAdapter["Gemini Adapter"]
        OpenRouterAdapter["OpenRouter Adapter"]
        CheaperInferenceAdapter["CheaperInference Adapter"]
    end

    subgraph VoiceWorker ["Voice AI Pipeline (Separate Worker Process)"]
        VAD["Voice Activity Detection (Silero VAD)"]
        STT["STT Engine (Whisper / OpenAI / LiveKit)"]
        LangDetect["Language Detector (EN / AR)"]
        TTS["TTS Engine (OpenAI / Gemini / Edge-TTS)"]
        LiveKitRoom["LiveKit WebRTC Room Session"]
    end

    subgraph Storage ["Persistence & Telemetry"]
        SQLite["SQLite WAL Mode (App State & Settings)"]
        UsageTracker["Centralized Cost & Telemetry Engine"]
    end

    UI --> Gateway
    AudioClient <--> LiveKitRoom
    FastAPI --> IntentManagement
    IntentManagement -- Conversational Intent --> Router
    IntentManagement -- Knowledge Intent --> RAGEngine
    RAGEngine --> Router
    Router --> Registry
    Registry --> OpenAIAdapter & GeminiAdapter & OpenRouterAdapter & CheaperInferenceAdapter
    LiveKitRoom --> VoiceWorker
    VoiceWorker --> IntentManagement
    FastAPI --> SQLite
    FastAPI --> UsageTracker
```

## Architectural Highlights
1. **Modular Monolith Backend**: FastAPI coordinates state, REST APIs, and background processing while delegating real-time audio streams to a non-blocking voice worker.
2. **Dual-Path Intent Routing**: Queries first evaluate intent before invoking dense/sparse retrieval to eliminate unnecessary vector computation on simple greetings.
3. **Decoupled Providers**: All external AI providers implement uniform protocols for LLM, STT, TTS, Embeddings, and Reranking.
4. **Resilient Local Persistence**: SQLite configured in Write-Ahead-Logging (WAL) mode guarantees high concurrency without lock contention during simultaneous ingestion and chat streaming.
