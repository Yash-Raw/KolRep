# VoiceRep — AI Voice Replication Platform

> **Upload an authorized voice once. Power both Studio narration and interactive Conversational AI agents.**

VoiceRep is an enterprise-grade AI voice platform built on a unified architectural principle: **one verified voice profile powers every audio experience**. Users upload or record an authorized voice sample, validate acoustic quality, and immediately unlock both high-fidelity Text-to-Speech narration in **Voice Studio** and real-time interactive microphone conversations in **Voice Agents**.

---

## Architecture Overview

```text
                                VoiceRep
                                   │
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
            Next.js Frontend                  FastAPI Backend
       (TypeScript, Tailwind 4)              (Python 3.11, asyncpg)
                   │                               │
                   └───────────────┬───────────────┘
                                   │
                           ElevenLabs Provider
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              Instant Voice    Streaming TTS   Conversational
                 Cloning       (V2 Models)     AI (WebSocket)
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                         Shared Voice Library
                                   │
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
              PostgreSQL         Redis       Cloudflare R2
              (SQLAlchemy 2)     (ARQ)       (Object Storage)
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, Lucide Icons |
| **Backend** | Python 3.11, FastAPI, Pydantic v2 |
| **Database** | PostgreSQL 16 (Supabase compatible), SQLAlchemy 2.0 (async), Alembic |
| **Authentication** | Supabase Auth with JWT verification (and dev fallback mode) |
| **Voice Cloning** | ElevenLabs Instant Voice Cloning (`POST /v1/voices/add`) |
| **Text-to-Speech** | ElevenLabs Streaming TTS (`eleven_multilingual_v2`, `eleven_turbo_v2_5`) |
| **Voice Agents** | ElevenLabs Conversational AI (`WebSocket` signed URLs) |
| **Audio Validation** | FFmpeg 9.0.2, ffprobe (`silencedetect`, `volumedetect`) |
| **Object Storage** | Cloudflare R2 / S3-compatible (with local disk fallback) |
| **Background Jobs** | Redis 7 + ARQ |
| **Testing** | Pytest, pytest-asyncio, httpx, aiosqlite |

---

## Core Features

### 🎙️ 1. Reusable Voice Library & Cloning
- **Multi-Format Ingestion**: Supports MP3, WAV, M4A, WebM, and MP4 (automatic video track stripping via FFmpeg).
- **Acoustic Quality Analysis**: Real-time extraction of duration, sample rate, channels, speech-to-silence ratio, and clipping detection.
- **Affirmative Speaker Authorization**: Strict consent logging with scope checkboxes (`speech_generation`, `ai_agent`) and relationship verification.
- **Full Voice Lifecycle**: `upload_pending` → `validating` → `cloning` → `ready` / `failed` → `deleting` → `deleted`.
- **Remote Revocation**: Deleting a voice permanently deletes the remote clone from ElevenLabs and deactivates dependent agents.

### 🎛️ 2. Module A: Voice Studio
- **Narration Editor**: Large formatted text area with character counters and length limits.
- **Precision Acoustic Sliders**: Stability, similarity boost, speaking tempo (0.5x–2.0x), and style exaggeration.
- **Refined Waveform Audio Player**: Custom audio player with play/pause, seek slider, time elapsed, mute toggle, and instant MP3 download.
- **Generation History**: Comprehensive log of all past audio generations with direct playback.

### 🤖 3. Module B: Voice Agents & Live Playground
- **Agent Configuration**: Custom persona names, descriptions, system prompts, first greetings, and languages.
- **Zero Real-time Overhead**: Uses ElevenLabs Conversational AI WebSocket protocol with dynamic per-session voice overrides.
- **Agent Playground**:
  - Microphone access and mute toggle.
  - Interactive visual status orb: *Connecting*, *Listening*, *Thinking*, *Speaking*.
  - Real-time turn transcripts for both User and Agent.
  - Native interruption support.

---

## Getting Started Locally

### 1. Prerequisites
- Node.js 20+ & npm
- Python 3.11+
- FFmpeg and ffprobe
- PostgreSQL 16 & Redis 7 (or Docker)

### 2. Clone and Configure Environment

```bash
git clone https://github.com/your-username/VoiceRep.git
cd VoiceRep

# Copy example environment configuration
cp .env.example .env
```

Edit `.env` with your credentials:
```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/voicerep
SYNC_DATABASE_URL=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/voicerep
REDIS_URL=redis://localhost:6379/0

# ElevenLabs (Required for live provider calls)
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_AGENT_ID=your_elevenlabs_agent_id
```

### 3. Run Migrations

```bash
cd backend
alembic upgrade head
```

### 4. Run the Backend API

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
API Documentation will be available at: `http://localhost:8000/docs`

### 5. Run the Frontend App

```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Running with Docker Compose

To start the entire platform (PostgreSQL, Redis, FastAPI, Background Worker, Next.js) with a single command:

```bash
docker compose up -d --build
```

---

## Running Automated Tests

Run the backend Pytest test suite:

```bash
cd backend
pytest -v
```

All 13 integration and unit tests will run against an isolated test database, verifying:
- End-to-end audio validation and FFmpeg conversion
- Instant voice cloning flows and consent logging
- Speech synthesis and character tracking
- Conversational agent creation and signed URL generation
- Strict cross-user ownership isolation

---

## Documentation

Detailed architectural and operational documentation is available in the [`docs/`](./docs) directory:
- [System Architecture](./docs/ARCHITECTURE.md)
- [REST API Reference](./docs/API.md)
- [Implementation Log](./docs/IMPLEMENTATION_LOG.md)
- [Production Deployment Guide](./docs/DEPLOYMENT.md)

---

## License

MIT © VoiceRep Platform.
