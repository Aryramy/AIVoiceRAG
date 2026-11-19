# VoiceRag — Testing & Quality Assurance Strategy

## 1. Testing Pyramid

```
       /\
      /  \     Browser E2E Tests (Playwright)
     /----\    Multilingual & Voice Turn Evaluation
    /      \   API & Service Integration Tests (pytest)
   /--------\  Unit Tests (Intent Classifier, RRF, Chunker)
```

## 2. Test Suites

### 2.1 Backend Unit & Integration Tests (`tests/`)
- **Intent Classification Tests**: Verify greetings ("Hi", "Hello", "Thanks", "مرحبا") bypass RAG and return conversational responses without DB access.
- **Chunking & Ingestion Tests**: Verify PDF, DOCX, XLSX parsing, page tracking, and chunk boundary preservation.
- **Hybrid Retrieval Tests**: Verify dense vector search + BM25 keyword search combine correctly via Reciprocal Rank Fusion.
- **Provider & Discovery Tests**:
  - OpenAI, Gemini, OpenRouter, and CheaperInference model discovery & capability registration.
  - Dynamic voice listing.
  - Connection test endpoints with masked credentials.
- **Smart Auto Router Tests**: Verify profile-based model selection (`low_cost`, `balanced`, `high_quality`) and fallback behavior.
- **Telemetry & Cost Tests**: Validate token tracking, latency recording, and pricing formulas.

### 2.2 Frontend & UI Tests (`frontend/`)
- **RTL & Typography**: Verify `dir="rtl"` switches direction correctly and mirrors navigation and icons.
- **Dynamic Settings Interface**: Verify selecting a provider fetches supported capabilities and dynamic model dropdowns without cross-capability resets.
- **Audio & Waveform State**: Verify listening, thinking, speaking, and interrupted state transitions.

### 2.3 RAG Quality Evaluation
- Representative evaluation dataset with 20+ English and Arabic questions.
- Metrics: Retrieval Precision@K, Citation Correctness, Answer Groundedness, and Abstention Accuracy.

