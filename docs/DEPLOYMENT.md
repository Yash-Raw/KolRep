# VoiceRep — Production Deployment Guide

## 1. Prerequisites

- Server: Ubuntu 22.04 LTS or macOS with Docker and Docker Compose installed.
- Domain with SSL certificate (e.g. `voicerep.yourdomain.com`).
- Managed PostgreSQL 15+ database (e.g. Supabase, AWS RDS, Neon).
- Managed Redis 7+ instance (e.g. Upstash, AWS ElastiCache).
- Cloudflare R2 bucket or AWS S3 bucket (optional, local disk storage supported).
- Apple Silicon (MPS) or NVIDIA (CUDA) GPU recommended for fastest local inference.

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

# 100% Local Voice Engine (F5-TTS DiT Flow Matching)
VOICE_PROVIDER=self_hosted
SELF_HOSTED_MODEL=F5TTS_v1_Base
SELF_HOSTED_DEVICE=auto
SELF_HOSTED_VOICE_DIR=./storage/voice_profiles
SELF_HOSTED_NFE_STEPS=32

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

## 5. 100% Self-Hosted Neural Engine Setup

VoiceRep v1.0 runs completely locally without external cloud API dependencies:
1. Model weights for F5-TTS and Whisper are automatically fetched from Hugging Face on first boot and cached in standard cache directories.
2. Ensure GPU acceleration is enabled (PyTorch with `mps` on macOS Apple Silicon or `cuda` on Linux with NVIDIA drivers).
3. Audio generation and voice profiles are saved locally inside `./storage`.
