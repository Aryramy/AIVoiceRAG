# VoiceRag — Known Issues & Limitations

1. **Local LiveKit Server Binary on Windows**:
   - LiveKit server runs best on Windows via standalone binary or Docker. When running purely in Windows without an active LiveKit server on port 7880, voice interaction falls back to direct WebSocket streaming and REST-based audio endpoints.
2. **Arabic Scanned PDFs**:
   - PDFs containing rasterized/scanned images of Arabic text require Tesseract OCR with `ara` training data for complete extraction. Text-based Arabic PDFs parse natively via `pypdf`.
3. **Browser Audio Autoplay Policies**:
   - Modern browsers block programmatic audio playback without prior user interaction. Users must click the Microphone or Speaker icon at least once to authorize audio playback.

