# VoiceRag — Feature Inventory & Traceability Matrix

| Feature ID | Module | Feature Description | Status | Verification Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **CHAT-01** | Conversational Assistant | Text chat with streaming token response & session memory | PLANNED | Real LLM token streaming via SSE / WebSocket |
| **CHAT-02** | Conversational Assistant | Intent Classification (Greeting vs Knowledge vs Noise) | PLANNED | Small talk does not trigger RAG; noise suppressed |
| **CHAT-03** | Conversational Assistant | Conversation management (Create, Rename, Delete, List) | PLANNED | Persistence across sessions in SQLite |
| **KB-01** | Knowledge Base | Multi-collection Knowledge Base Management (CRUD) | PLANNED | Create, rename, view doc counts, rebuild index |
| **KB-02** | Ingestion Engine | Document processing (PDF, DOCX, XLSX, CSV, TXT, MD) | PLANNED | Real parsing, metadata preservation, chunking |
| **KB-03** | Ingestion Engine | Multilingual Embedding & Qdrant vector indexing | PLANNED | Dense embeddings stored in Qdrant with doc metadata |
| **RAG-01** | Advanced RAG | Hybrid Search (Qdrant Dense + BM25 Sparse + RRF) | PLANNED | Combined score retrieval with configurable top-K |
| **RAG-02** | Advanced RAG | Cross-Encoder Reranking & Threshold Filtering | PLANNED | Relevant passages boosted; low-confidence filtered |
| **RAG-03** | Advanced RAG | Grounded Generation with Traceable Citations | PLANNED | Clickable source references with page & chunk highlight |
| **RAG-04** | Advanced RAG | Honest Abstention Policy | PLANNED | No hallucination when sources lack relevant answers |
| **LANG-01** | Multilingual | English & Arabic Speech Recognition (STT) | PLANNED | Whisper/LiveKit STT accurate for EN and AR |
| **LANG-02** | Multilingual | English & Arabic Speech Synthesis (TTS) | PLANNED | Natural voice synthesis in English and Arabic |
| **LANG-03** | Multilingual | Arabic RTL interface & typography | PLANNED | Full direction-aware UI, mirroring, and font styling |
| **VOICE-01** | Voice AI Engine | Real-time WebRTC audio transport via LiveKit | PLANNED | Sub-second latency turn-taking, room connection |
| **VOICE-02** | Voice AI Engine | VAD & Interruption / Barge-in | PLANNED | User speaking interrupts ongoing assistant TTS |
| **PROV-01** | Provider Architecture| Dynamic AI Provider & Model Config (9 categories) | PLANNED | Dropdown dynamically lists live models & voices |
| **PROV-02** | Provider Architecture| Independent capability selection (LLM, STT, TTS, Voice)| PLANNED | Split provider configuration without cross-reset |
| **ROUT-01** | Smart Auto Router | Routing Profiles (Low Cost, Balanced, High Quality) | PLANNED | Dynamic provider/model dispatch with fallback |
| **COST-01** | Analytics & Cost | Telemetry (Tokens, Audio seconds, Latency, Cost) | PLANNED | Real calculation per request using pricing registry |
| **ADMIN-01**| Administration | Comprehensive 9-domain Settings Dashboard | PLANNED | Real backend persistence and diagnostic health check |
| **SEC-01** | Security | API Key masking, Input validation, Tenant safety | PLANNED | Zero credential leakage in client responses |

