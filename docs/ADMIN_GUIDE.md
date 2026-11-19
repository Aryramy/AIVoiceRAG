# VoiceRag — Administration & Configuration Guide

## 1. Administration Settings Domains
Administrators configure runtime behavior under **Settings**:

### 1. AI Provider and Model Configuration
- Dynamically select provider (**OpenAI**, **Google Gemini**, **OpenRouter**, **CheaperInference**, or **Smart Auto Router**).
- Dynamically populate available models from official provider APIs.
- Independently configure LLM, STT, TTS, and Voice without forcing unified provider coupling.
- Click **Test Connection** to verify API keys and network latency.
- Click **Refresh Models** to purge cached catalogs and query latest provider releases.

### 2. Smart Auto Router Configuration
- Enable or disable auto-routing.
- Choose profile: `Low Cost`, `Balanced`, `High Quality`, or `Maximum Capability`.
- Define fallback sequences and max retry limits.

### 3. STT Configuration
- Select speech recognition provider (OpenAI Whisper or provider native).
- Configure language auto-detection and speech confidence thresholds.

### 4. TTS Configuration
- Select speech synthesis provider (OpenAI, Gemini, Edge-TTS).
- Preview voices with instant audio playback.

### 5. Voice & Language Settings
- Default response language (`Auto`, `English`, `Arabic`).
- Turn-taking silence duration (default `500ms`).

### 6. RAG & Retrieval Configuration
- Hybrid search weight balance (Dense vs BM25).
- Retrieval top-K (default `5`) and cross-encoder reranking toggle.
- Abstention similarity threshold (default `0.35`).

### 7. Security and Access Control
- API key management and masking.
- Role-Based Access Control (Admin, Operator, User).

### 8. Integrations & API
- LiveKit WebRTC server URLs and credentials.
- Webhook endpoints.

### 9. System Health and Diagnostics
- Live status indicators for Database, Qdrant Vector DB, Provider APIs, and Voice Worker.
