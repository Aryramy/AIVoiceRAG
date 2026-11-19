# VoiceRag — Troubleshooting Guide

## 1. Common Issues & Resolutions

### 1.1 WebRTC / LiveKit Connection Fails
- **Symptom**: Microphone activates but audio does not stream, or client reports `ConnectionTimeout`.
- **Cause**: LiveKit server is unreachable or credentials in `.env` are mismatched.
- **Resolution**:
  - Verify LiveKit server is running on `ws://127.0.0.1:7880`.
  - Check `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` match between backend `.env` and LiveKit server configuration.

### 1.2 Provider Connection Test Returns 401 Unauthorized
- **Symptom**: "Invalid API Key" error during connection test.
- **Resolution**:
  - Verify credentials in `Settings -> AI Provider Configuration`.
  - Confirm base URL is correct (e.g. `https://openrouter.ai/api/v1` for OpenRouter).

### 1.3 Arabic Text Appears Reversed or Disconnected
- **Symptom**: Arabic letters render disconnected or left-to-right.
- **Resolution**:
  - Ensure the parent container has `dir="rtl"`.
  - Verify `lang="ar"` attribute is set.

### 1.4 Database Locked in SQLite
- **Symptom**: `sqlite3.OperationalError: database is locked`.
- **Resolution**:
  - VoiceRag initializes SQLite with `PRAGMA journal_mode=WAL;` and `PRAGMA busy_timeout=5000;`.
  - Ensure no external process has opened the `.db` file in an exclusive lock mode.

