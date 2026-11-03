# VoiceRep — Production Deployment Guide

## 1. Prerequisites

- Server: Ubuntu 22.04 LTS or macOS with Docker and Docker Compose installed.
- Domain with SSL certificate (e.g. `voicerep.yourdomain.com`).
- Managed PostgreSQL 15+ database (e.g. Supabase, AWS RDS, Neon).
- Managed Redis 7+ instance (e.g. Upstash, AWS ElastiCache).
- Cloudflare R2 bucket or AWS S3 bucket.
- ElevenLabs account with an API Key and configured Conversational AI Agent.

---

## 2. Environment Variables Checklist

Configure the following environment variables in your production environment:

```dotenv
# Application
APP_ENV=production
APP_SECRET_KEY=generate-a-strong-random-64-char-secret-key
FRONTEND_URL=https://voicerep.yourdomain.com
BACKEND_URL=https://api.voicerep.yourdomain.com

# Database (Supabase PostgreSQL / AsyncPG)
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/voicerep
SYNC_DATABASE_URL=postgresql+psycopg2://user:password@db-host:5432/voicerep

# Supabase Auth
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_JWKS_URL=https://your-project.supabase.co/rest/v1/auth/v1/.well-known/jwks.json

# ElevenLabs Provider
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_AGENT_ID=your-shared-elevenlabs-convai-agent-id

# Object Storage (Cloudflare R2 / S3)
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=voicerep-storage
R2_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com

# Redis & Background Workers
REDIS_URL=rediss://default:password@your-redis-host:6379/0

# Upload Limits
MAX_UPLOAD_SIZE_MB=50
MAX_AUDIO_DURATION_SECONDS=300
```

---

## 3. Database Migrations

Apply migrations to initialize all tables, constraints, and indexes:

```bash
cd backend
alembic upgrade head
```

---

## 4. Docker Compose Deployment

A complete production `docker-compose.yml` is included in the root directory:

```bash
# Build and start all containers in detached mode
docker compose up -d --build

# Inspect logs
docker compose logs -f backend
```

Services started:
- `db`: PostgreSQL 16
- `redis`: Redis 7
- `backend`: FastAPI API server listening on `:8000`
- `worker`: ARQ background worker executing async synthesis jobs
- `frontend`: Next.js 16 production server listening on `:3000`

---

## 5. ElevenLabs Conversational AI Setup Instructions

To enable Module B (Voice Agents):

1. Log into your [ElevenLabs Dashboard](https://elevenlabs.io/).
2. Navigate to **Conversational AI** > **Create Agent**.
3. Configure the agent:
   - Name: `VoiceRep Shared Agent`
   - Language: `English (en)`
   - LLM: Choose `gemini-1.5-flash` or `gpt-4o-mini`
   - TTS Model: `eleven_turbo_v2_5`
4. Under **Agent Settings** > **Security & Overrides**:
   - Enable **Dynamic Voice ID Override**: Check `tts.voice_id`.
   - Enable **Prompt Overrides**: Check `agent.prompt.prompt`, `agent.first_message`, `agent.language`.
5. Copy the Agent ID from the URL or settings and paste it into `.env` as:
   ```dotenv
   ELEVENLABS_AGENT_ID=<your-agent-id>
   ```
6. Add your API Key as `ELEVENLABS_API_KEY`.
