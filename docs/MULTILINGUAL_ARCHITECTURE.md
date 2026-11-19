# VoiceRag — Multilingual Architecture (English & Arabic)

## 1. Scope & Strategy
Arabic and English are the two first-class mandatory languages in VoiceRag. The architecture addresses language awareness at every tier:
1. **Frontend / UX Tier**:
   - Right-to-Left (RTL) layout switching via `dir="rtl"`.
   - Direction-aware layout mirroring: Left sidebar swaps to Right sidebar in RTL; icons with directional meaning (back/forward arrows, send indicators) mirror automatically.
   - High-readability Arabic typography with appropriate line-heights (1.6+) for diacritics.
2. **Speech Tier**:
   - STT: Whisper and LiveKit STT language auto-detection targeting ISO-639-1 `ar` and `en`.
   - TTS: High-naturalness Arabic voices (e.g., Arabic neural voices `ar-SA-HamedNeural`, `ar-EG-SalmaNeural` via Edge-TTS / OpenAI Arabic support).
3. **Retrieval & RAG Tier**:
   - Multilingual dense vector space: preserves cross-lingual query-to-document alignment. An Arabic query can retrieve an English source and synthesize an Arabic grounded answer (or vice-versa).
   - Arabic text normalization (alef normalization, teh marbuta handling, tashkeel stripping for sparse BM25 indexing).
4. **Conversational Intent**:
   - Understands common Arabic greetings and acknowledgments (`مرحبا`, `أهلا`, `شكرا`, `يعطيك العافية`) as direct conversational intent without triggering RAG database abstention.
