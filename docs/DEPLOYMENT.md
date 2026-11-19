# VoiceRag — Deployment & Operations Guide

## 1. Local Development (Windows)

### Prerequisites
- Python 3.12+ (64-bit)
- Node.js 20+ & `npm.cmd`
- LiveKit Server (local binary or docker `livekit/livekit-server`)

### Steps
1. **Initialize Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Populate OPENROUTER_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, CHEAPER_INFERENCE_API_KEY, etc.
   ```
3. **Database Setup & Migrations**:
   ```bash
   .\venv\Scripts\python.exe -m alembic upgrade head
   ```
4. **Run FastAPI Backend**:
   ```bash
   .\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. **Run Frontend**:
   ```bash
   cd frontend
   npm.cmd install
   npm.cmd run dev
   ```
6. **Access UI**:
   - Web application: `http://localhost:3000`
   - Backend OpenAPI documentation: `http://localhost:8000/docs`

---

## 2. Production Deployment
- **Backend**: Containerized FastAPI behind reverse proxy (Nginx or Caddy) with Gunicorn/Uvicorn workers.
- **Frontend**: Next.js standalone output hosted on Node.js container or Vercel.
- **Vector Database**: Standalone clustered Qdrant with persistent volume mounts.
- **LiveKit Server**: Clustered LiveKit WebRTC SFU with Coturn STUN/TURN for NAT traversal.
- **Database**: PostgreSQL with connection pooling (e.g. PgBouncer) for high scale.
