# VoiceRag — Security & Privacy Architecture

## 1. Threat Model & Security Posture
VoiceRag is designed with a defense-in-depth security posture, addressing:
- Credential protection (API keys, LiveKit secrets, database credentials).
- File upload security & malicious binary mitigation.
- SSRF (Server-Side Request Forgery) protection on URL/web crawling.
- Tenant & session isolation.
- Sensitive data redaction in logging.

## 2. Security Controls

### 2.1 Credential & Secret Management
- API keys (OpenAI, Gemini, OpenRouter, CheaperInference) stored in SQLite are encrypted/masked at rest and in transit.
- Public responses never return raw API keys. A dedicated masking algorithm (`sk-****1234`) is applied before JSON serialization.
- `.env` files are excluded via `.gitignore` with strict environment variable injection.

### 2.2 Upload Validation & File Safety
- Allowed MIME types strictly enforced:
  - `application/pdf`
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  - `text/plain`
  - `text/markdown`
  - `text/csv`
- File size capped at 50MB per document.
- Filenames sanitized to prevent path traversal (`../`) vulnerabilities.
- Uploaded files staged in a non-executable private directory (`./data/uploads/`).

### 2.3 SSRF Protection
- For URL/web knowledge sources:
  - IP resolution pre-checks prevent queries to private RFC-1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`).
  - Strict protocol enforcement (`https://` only; non-standard ports blocked).

### 2.4 Data Privacy & Tenant Isolation
- Knowledge bases and conversations are scoped with strict relational foreign keys.
- Vector search queries in Qdrant enforce mandatory payload filtering on `knowledge_base_id` to guarantee zero cross-tenant passage leakage.

