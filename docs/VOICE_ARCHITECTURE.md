# VoiceRag — Real-Time Voice AI Architecture

## 1. Real-Time Pipeline Overview
VoiceRag provides a low-latency voice interaction pipeline combining **LiveKit WebRTC**, **Voice Activity Detection (Silero VAD)**, **Speech-to-Text (STT)**, and **Text-to-Speech (TTS)**.

```
+-------------------------------------------------------------------+
|                        Client Audio Tier                          |
|  Microphone -> WebAudio Analyser -> WebRTC Transport (LiveKit)    |
+-------------------------------------------------------------------+
                               |
                               v
+-------------------------------------------------------------------+
|                      LiveKit Voice Worker                         |
|  1. Ingress Audio Stream                                          |
|  2. Voice Activity Detection (Silero VAD, 30ms frames)            |
|  3. Speech-End Detection & Silence Threshold                      |
|  4. Streaming / Chunked STT (OpenAI Whisper / Provider STT)       |
|  5. Language Detection (Arabic vs English)                        |
|  6. Intent Classification:                                        |
|     - Conversational / Small Talk -> Immediate Direct Response    |
|     - Knowledge Query -> Trigger Hybrid RAG                       |
|     - Environmental Noise -> Suppress Response                    |
|  7. Streaming LLM Synthesis                                       |
|  8. Streaming TTS (OpenAI TTS / Gemini / Edge-TTS)                |
|  9. Egress Audio Stream -> Client Speaker                         |
+-------------------------------------------------------------------+
```

## 2. Low-Latency Voice Turn Management
1. **Voice Activity Detection (VAD)**:
   - Evaluates audio frame energy and voice probability using Silero VAD.
   - Silence threshold: 500ms continuous silence marks utterance completion.
2. **Barge-In / Interruption**:
   - If the user begins speaking while assistant TTS playback is active, the worker immediately issues an audio cancellation packet to the client and terminates downstream LLM/TTS generation.
3. **Intent-Gated RAG Execution**:
   - Small utterances such as "Hello", "Thanks", "Great", or "Can you hear me?" bypass the RAG engine and are answered instantaneously with sub-300ms time-to-first-token.
4. **Resilient Audio Fallback**:
   - When external provider TTS has high latency or rate limits, the built-in neural Edge-TTS synthesis acts as an immediate zero-cost fallback for Arabic and English.
