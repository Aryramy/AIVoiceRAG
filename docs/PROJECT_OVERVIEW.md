# VoiceRag — Project Overview

## 1. Executive Summary
**VoiceRag** is an enterprise-grade, multilingual AI Voice & Knowledge Assistant platform designed for seamless real-time natural conversational audio and text interactions in **English** and **Arabic**, backed by grounded Private Knowledge Base Retrieval (RAG).

The platform bridges real-time voice conversations (sub-second turn latency with LiveKit WebRTC, VAD, and streaming STT/TTS) with hybrid retrieval-augmented generation (BM25 keyword search, Qdrant dense vector search, reciprocal rank fusion, cross-encoder reranking, and citation traceability).

## 2. Core Pillars
1. **Multilingual First-Class (English & Arabic)**:
   - Real-time STT and natural TTS in both languages.
   - Arabic RTL (right-to-left) visual hierarchy, direction-aware layout, and typography.
   - Multilingual dense vector embeddings preserving Arabic semantic similarity.
2. **Intent-Driven Turn Management**:
   - Explicit conversational intent classification prior to RAG execution: distinguishes greetings, acknowledgments, and small talk from deep knowledge queries.
   - Environmental noise and background speech suppression to avoid phantom retrieval or unnecessary hallucinations.
3. **Dynamic Provider Independence**:
   - Universal capability matrix supporting **OpenAI**, **Google Gemini**, **OpenRouter**, and **CheaperInference**.
   - Dynamic model & voice discovery via official API catalogs with zero hardcoding.
   - Independent capability selection: configure one provider for LLM, another for STT, and another for TTS.
4. **Smart Auto Router**:
   - Application-level routing policies (`Low Cost`, `Balanced`, `High Quality`, `Maximum Capability`) with capability filtering, automatic fallbacks, circuit breaking, and latency tracking.
5. **Private Knowledge Base & Verifiable Grounding**:
   - Multi-format ingestion: PDF, DOCX, XLSX, CSV, TXT, Markdown.
   - Grounded responses with verifiable page-level and passage-level citations.
   - Explicit, honest abstention when evidence is insufficient.
6. **Telemetry, Cost Tracking & Diagnostics**:
   - Centralized pricing engine calculating input/output token costs, audio processing costs, and end-to-end latencies.
   - Production administration dashboard with 9 major configuration domains.
