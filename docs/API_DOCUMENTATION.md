# VoiceRag — API Documentation

Base URL: `/api/v1`

## 1. System & Health
- `GET /healthz`: Basic system health & uptime.
- `GET /api/v1/health`: Detailed subsystem diagnostics (Database, Vector DB, AI Providers, Storage).

## 2. Conversations & Messaging
- `POST /api/v1/conversations`: Create a new conversation session.
  - Body: `{"title": "string", "knowledge_base_id": "uuid | null", "language": "auto | en | ar", "mode": "hybrid | chat | rag_strict | rag_first"}`
- `GET /api/v1/conversations`: List all conversation sessions with pagination.
- `GET /api/v1/conversations/{id}`: Retrieve conversation details with message history.
- `DELETE /api/v1/conversations/{id}`: Delete conversation and cascade message history.
- `POST /api/v1/conversations/{id}/messages`: Post user message and receive streaming response (SSE) or JSON.
  - Body: `{"content": "string", "audio_base64": "string | null", "stream": true}`
  - Response: Server-Sent Events (SSE) streaming tokens, citations, and telemetry.

## 3. Knowledge Base & Documents
- `GET /api/v1/knowledge-bases`: List all knowledge bases with doc count & chunk count.
- `POST /api/v1/knowledge-bases`: Create a knowledge base.
  - Body: `{"name": "string", "description": "string", "embedding_model": "string"}`
- `GET /api/v1/knowledge-bases/{id}`: Get knowledge base details and documents.
- `DELETE /api/v1/knowledge-bases/{id}`: Delete knowledge base and drop vector collection.
- `POST /api/v1/knowledge-bases/{id}/documents/upload`: Upload file (multipart/form-data: PDF, DOCX, XLSX, TXT, MD).
- `GET /api/v1/knowledge-bases/{id}/documents`: List documents with indexing status.
- `DELETE /api/v1/documents/{doc_id}`: Remove document and clean vector points.
- `POST /api/v1/documents/{doc_id}/reprocess`: Trigger re-chunking and re-embedding.

## 4. RAG Retrieval & Testing
- `POST /api/v1/rag/retrieve`: Execute hybrid query retrieval test.
  - Body: `{"knowledge_base_id": "uuid", "query": "string", "top_k": 5, "use_reranker": true}`
  - Returns: Array of retrieved chunks with dense score, sparse score, RRF score, and reranker score.

## 5. Dynamic AI Providers & Model Discovery
- `GET /api/v1/providers`: List supported providers and their enabled status.
- `GET /api/v1/providers/{provider}/capabilities`: Return capability map (`llm`, `stt`, `tts`, `embeddings`, `reranker`).
- `GET /api/v1/providers/{provider}/models?capability={llm|stt|tts|embeddings}`: Dynamically discover supported models for that provider.
- `GET /api/v1/providers/{provider}/voices?model={model}&language={language}`: Retrieve compatible voices for the provider's TTS model.
- `POST /api/v1/providers/{provider}/test`: Validate connectivity with provider API credentials.
- `POST /api/v1/providers/{provider}/refresh`: Force cache invalidation and refresh model catalog.

## 6. AI Settings & Router Configuration
- `GET /api/v1/settings/ai`: Retrieve active AI configuration (LLM, STT, TTS, Voice, Router).
- `PUT /api/v1/settings/ai`: Update and persist active AI configuration.
- `GET /api/v1/router/profiles`: List available routing profiles (`low_cost`, `balanced`, `high_quality`, `max_capability`).

## 7. Real-Time Voice & WebRTC
- `POST /api/v1/voice/token`: Generate LiveKit WebRTC room token for the client.
  - Body: `{"conversation_id": "uuid", "participant_name": "string"}`
  - Returns: `{"token": "jwt_token", "url": "ws_url", "room_name": "string"}`

## 8. Telemetry & Analytics
- `GET /api/v1/analytics/summary`: Aggregate token usage, total estimated cost, average latency.
- `GET /api/v1/analytics/usage`: Detailed request logs with date, provider, and model filtering.
- `GET /api/v1/analytics/costs`: Cost breakdown by provider and capability.
