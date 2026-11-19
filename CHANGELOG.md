# Changelog

All notable changes to the VoiceRag project will be documented in this file.

## [1.0.0] - 2026-11-19
### Added
- **Full Backend Platform**:
  - FastAPI modular monolith running in Python 3.12 with SQLite WAL engine and SQLAlchemy 2.0 ORM.
  - Full data models: `User`, `Conversation`, `Message`, `KnowledgeBase`, `Document`, `DocumentChunk`, `MessageCitation`, `AISettings`, `UsageLog`.
  - Multi-format structure-aware document parser and chunker for PDF, DOCX, XLSX, TXT, and Markdown.
  - Hybrid RAG search engine with persistent local Qdrant dense vector store, BM25Okapi sparse search, and Reciprocal Rank Fusion (RRF).
  - Grounded citation generation (`[1]`, `[2]`) with chunk-level attribution and hallucination abstention.
  - Sub-millisecond conversational intent gating classifying greetings, gratitude, small talk, knowledge queries, and noise in English and Arabic.
  - Dynamic AI Provider Adapters with live discovery and capability extraction for OpenAI, Google Gemini, OpenRouter, CheaperInference, and Microsoft Edge TTS.
  - Smart Auto Router dynamically selecting models based on cost, workload, and complexity with circuit-breaker fallback.
  - Centralized cost and token telemetry engine tracking requests and spend in USD.
  - LiveKit WebRTC room token generator.
  - Automated test suite with 17 tests in `tests/` achieving 100% pass rate.

- **Full Modern Frontend Experience**:
  - Next.js 15, TypeScript, and Tailwind CSS web application in `frontend/`.
  - 3-area layout inspired by ChatGPT, Gemini, and NotebookLM:
    - Left sidebar with conversations history, search, and knowledge base selector.
    - Main chat workspace with distinct bubbles, citations badges, copy, and read-out-loud neural speech button.
    - Right collapsible contextual panel with document upload dropzone, document chunks, and citation inspector.
  - First-class Arabic RTL layout mirroring (`dir="rtl"`) with Cairo/Tajawal font stack.
  - Dedicated Voice Wave Modal with animated canvas audio waveform, ambient state glow, microphone controls, and assistant interruption.
  - Comprehensive AI Provider & Model Configuration settings page (`/settings`) with live connection testing, independent capability mapping, RAG tuning sliders, and bilingual system prompt editors.
  - Analytics and Cost Telemetry dashboard (`/analytics`) with live KPI metrics, provider spend breakdown, and recent invocation logs.

## [0.1.0] - 2026-11-19
### Added
- Phase 0: Complete system architecture, database schema, API documentation, and threat modeling in `docs/`.
- Greenfield project initialization with `.env.example`, `.gitignore`, and initial requirements.
- Core package environment initialization for FastAPI, SQLAlchemy, Qdrant, FastEmbed, and LiveKit.
