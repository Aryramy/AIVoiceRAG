# VoiceRag — Enterprise Multilingual AI Voice & Knowledge Assistant

> **Greenfield Development | English + Arabic | End-to-End Enterprise Platform**

VoiceRag is a production-oriented AI voice and knowledge platform built for low-latency conversational interaction and grounded private document retrieval in both English and Arabic.

---

## 🌟 Key Features
- **ChatGPT-Inspired Conversational Chat**: Minimalist conversation workspace with persistent history, message branching, and markdown formatting.
- **Gemini-Inspired Visual Hierarchy**: High-polish aesthetic, modern typography, responsive layout, and smooth animations.
- **NotebookLM-Inspired Knowledge Workspace**: Verifiable citations with clickable source passage highlighting and document management.
- **First-Class Arabic & RTL**: Direction-aware navigation, mirrorable icons, and Arabic neural speech synthesis.
- **Dynamic Provider Independence**: Pluggable adapters for **OpenAI**, **Google Gemini**, **OpenRouter**, and **CheaperInference** with live model and voice discovery.
- **Independent AI Capability Selection**: Select separate providers for LLM, STT, TTS, and Voice.
- **Smart Auto Router**: Policy-driven routing (Low Cost, Balanced, High Quality, Maximum Capability) with automatic fallback and circuit breaking.
- **Hybrid RAG Engine**: Qdrant dense vector search combined with BM25 sparse keyword search and Reciprocal Rank Fusion (RRF).
- **Real-Time Voice AI**: WebRTC audio streaming, Voice Activity Detection (VAD), conversational turn management, and barge-in / interruption handling.
- **Enterprise Cost & Telemetry**: Centralized token, audio duration, and financial cost tracking with a 9-domain administrative dashboard.

---

## 📂 Documentation
- [System Architecture](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/SYSTEM_ARCHITECTURE.md)
- [Feature Inventory](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/FEATURE_INVENTORY.md)
- [Database Schema](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/DATABASE_SCHEMA.md)
- [API Documentation](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/API_DOCUMENTATION.md)
- [RAG Architecture](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/RAG_ARCHITECTURE.md)
- [Voice Architecture](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/VOICE_ARCHITECTURE.md)
- [Multilingual Architecture](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/MULTILINGUAL_ARCHITECTURE.md)
- [Provider Architecture](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/PROVIDER_ARCHITECTURE.md)
- [Smart Router](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/SMART_ROUTER.md)
- [Security](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/SECURITY.md)
- [Deployment](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/DEPLOYMENT.md)
- [Testing Strategy](file:///c:/Users/aurehman6521/Desktop/AI%20Projects/AIVoiceRAG/docs/TESTING_STRATEGY.md)

---

## 🚀 Quick Start
```bash
# 1. Setup virtual environment and dependencies
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env

# 3. Start Backend
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000

# 4. Start Frontend
cd frontend
npm.cmd install
npm.cmd run dev
```
