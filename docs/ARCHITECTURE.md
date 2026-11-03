# VoiceRep — System Architecture Documentation

## 1. Executive Summary

VoiceRep is an AI voice replication and conversational agent platform designed around a fundamental product principle: **"Upload once, deploy everywhere."**

Users record or upload an authorized voice sample once, generating a reusable high-fidelity acoustic profile stored in PostgreSQL and ElevenLabs. This single profile powers two distinct modules:
- **Module A: Voice Studio**: Studio-grade text-to-speech generation with granular acoustic controls (stability, similarity boost, speaking speed, style exaggeration) and instantaneous waveform playback and download.
- **Module B: Voice Agents**: Real-time conversational AI voice agents with live microphone streaming, low-latency WebSocket communication, turn detection, transcript streaming, and voice interruption.

---

## 2. Logical Architecture Diagram

```text
                                +---------------------------+
                                |      Next.js Frontend     |
                                |  (TypeScript, Tailwind 4) |
                                +-------------+-------------+
                                              |
                              HTTPS / REST    |   WebSocket (ConvAI)
                                              |
                                              v
                                +---------------------------+
                                |        FastAPI API        |
                                |       (Python 3.11)       |
                                +-------------+-------------+
                                              |
                   +--------------------------+--------------------------+
                   |                          |                          |
                   v                          v                          v
       +-----------------------+  +-----------------------+  +-----------------------+
       |     Voice Service     |  |     Studio Service    |  |     Agent Service     |
       |  - Validation Report  |  |  - Text-to-Speech     |  |  - ConvAI Session     |
       |  - Audio Conversion   |  |  - Character Tracking |  |  - Prompt Overrides   |
       |  - Speaker Consent    |  |  - Waveform Export    |  |  - Signed URL Auth    |
       +-----------+-----------+  +-----------+-----------+  +-----------+-----------+
                   |                          |                          |
                   +--------------------------+--------------------------+
                                              |
                                              v
                               +-----------------------------+
                               |     Provider Abstraction    |
                               |    (VoiceProvider Interface)|
                               +--------------+--------------+
                                              |
                                              v
                               +-----------------------------+
                               |      ElevenLabs Provider    |
                               |  - Instant Voice Cloning    |
                               |  - TTS Multilingual v2      |
                               |  - Conversational AI (WSS)  |
                               +--------------+--------------+
                                              |
             +--------------------------------+--------------------------------+
             |                                |                                |
             v                                v                                v
+--------------------------+    +--------------------------+    +--------------------------+
|   PostgreSQL Database    |    |      Redis + ARQ         |    |      Cloudflare R2       |
|  - Users                 |    |  - Async Background Jobs |    |  - Private Sample Audio  |
|  - Voices & Consents     |    |  - Long-form Narration   |    |  - Studio Output Audio   |
|  - Generations & Agents  |    +--------------------------+    +--------------------------+
+--------------------------+
```

---

## 3. Component Responsibilities

### 3.1 Next.js Frontend
- Located in `/frontend`.
- Built with Next.js (App Router), TypeScript, and Tailwind CSS.
- **Client Responsibilities**:
  - Handles client-side audio recording and drag-and-drop file ingestion.
  - Multi-step modal for voice cloning with explicit speaker authorization checks.
  - Interactive Voice Studio with live character counter, slider adjustments, and audio player.
  - Interactive Agent Playground with microphone capture via `navigator.mediaDevices.getUserMedia` and WebSocket streaming to ElevenLabs Conversational AI.

### 3.2 FastAPI Backend
- Located in `/backend`.
- **Backend Responsibilities**:
  - Supabase JWT authentication and user session enforcement.
  - Strict resource ownership verification on every database query (preventing IDOR vulnerabilities).
  - Audio processing pipeline via FFmpeg/ffprobe: duration extraction, silence detection, clipping analysis, and WAV normalization.
  - ElevenLabs API provider integration keeping all secrets server-side.
  - Cloudflare R2 / S3 presigned URL generation and storage management.

### 3.3 Provider Layer Abstraction
- Defined in `app/providers/base.py` as `VoiceProvider`.
- Decouples business logic from ElevenLabs SDK specifics, enabling pluggable future providers (Cartesia, OpenAI Custom Voices, Fish Audio) without modifying database schemas or frontend interfaces.

### 3.4 Data & Storage Layer
- **PostgreSQL 16**: Managed via SQLAlchemy 2.0 (asyncio) and versioned with Alembic.
- **Redis 7 & ARQ**: Background queue for asynchronous synthesis jobs.
- **Cloudflare R2**: Object storage for temporary sample files and generated MP3 audio, accessed exclusively via short-lived presigned URLs.

---

## 4. Audio Processing & Quality Pipeline

1. **Ingestion**: Accepts MP3, WAV, M4A, WebM, MP4. Files over 50MB are rejected with HTTP 413.
2. **Metadata Inspection**: `ffprobe` extracts codec, duration, sample rate, and channels.
3. **Acoustic Analysis**:
   - `silencedetect=noise=-30dB:d=0.5` computes speech-to-silence ratio.
   - `volumedetect` checks peak dB levels to detect digital clipping or distortion.
4. **WAV Conversion**: Audio extracted from video containers or non-standard sample rates is converted into standard 44.1kHz mono PCM WAV for optimal acoustic cloning.
5. **Quality Scoring**: Categorized as `good`, `acceptable`, or `poor` with actionable warnings returned to the user.

---

## 5. Agent Session Lifecycle

```text
User Browser             FastAPI API                 ElevenLabs API
     |                        |                            |
     | 1. POST /agents/{id}/session                        |
     +----------------------->|                            |
     |                        | 2. Verify User Ownership   |
     |                        | 3. Verify Voice 'ready'    |
     |                        |                            |
     |                        | 4. GET /convai/get-signed-url
     |                        +--------------------------->|
     |                        |<---------------------------+
     |                        |    Returns signed WSS URL  |
     | 5. Signed URL & Config |                            |
     |<-----------------------+                            |
     |                                                     |
     | 6. Establish WSS Connection with Signed URL         |
     +---------------------------------------------------->|
     |                                                     |
     | 7. Send initiation config with cloned voice_id      |
     +---------------------------------------------------->|
     |                                                     |
     | 8. Bi-directional real-time audio & transcripts     |
     |<===================================================>|
```
