# VoiceRep — 100% Local AI Voice Cloning Platform

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](https://python.org)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![PyTorch MPS/CUDA](https://img.shields.io/badge/PyTorch-MPS%20%7C%20CUDA-red.svg)](https://pytorch.org)
[![Cloud Cost: $0.00](https://img.shields.io/badge/Cloud_Cost-$0.00-brightgreen.svg)]()

> **Clone an authorized voice locally in seconds. Power high-fidelity studio narration with zero cloud costs and 100% privacy.**

VoiceRep is an enterprise-grade, open-source AI voice platform engineered for **100% local, self-hosted execution**. Built on modern **Conditional Flow Matching Diffusion Transformers (F5-TTS DiT)** and **Whisper ASR**, VoiceRep requires zero external APIs, zero credit cards, and zero cloud bills.

---

## 🏗️ Architecture Overview

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
               100% Local Neural Engine (F5-TTS + Whisper)
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             Zero-Shot Voice    Diffusion TTS     In-Browser
                 Cloning        (Flow Matching)   Mic Recording
                    │              │              │
                    └──────────────┼──────────────┘
                                   │
                         Shared Voice Library
                                   │
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
              PostgreSQL         Redis        Local Disk
            (SQLAlchemy 2)       (ARQ)        (./storage)
```

---

## ⚡ Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, Lucide Icons |
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn |
| **Voice Cloning Engine** | F5-TTS Base (`F5TTS_v1_Base`) Conditional Flow Matching DiT |
| **Acoustic Alignment** | OpenAI Whisper (`whisper-tiny` / `whisper-base`) for phoneme text-audio alignment |
| **Audio Processing** | FFmpeg 9.0.2 (`silencedetect`, `volumedetect`), SoundFile, Librosa |
| **Hardware Acceleration** | Apple Silicon (`mps`), NVIDIA CUDA (`cuda`), CPU fallback |
| **Database & Cache** | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic, Redis 7 + ARQ |
| **Storage** | 100% Local filesystem (`./storage`) with directory traversal protection |
| **License** | GNU Affero General Public License v3.0 (AGPL-3.0) |

---

## 💡 Why VoiceRep? (Feature Comparison)

| Dimension | VoiceRep | VoiceStudio (`debpalash/VoiceStudio`) | ElevenLabs |
| :--- | :--- | :--- | :--- |
| **Cost** | **$0.00 (Free & Open Source)** | $0.00 (Free & Open Source) | Paid ($$$ per character) |
| **Privacy** | **100% Local / Air-Gapped** | 100% Local | Data sent to cloud |
| **Architecture** | **Full-Stack Web & REST API** | Electron desktop app | Proprietary SaaS |
| **Cloning Method** | Zero-Shot Flow Matching DiT | Multi-engine (F5, Cosy, Melo) | Proprietary Closed Weights |
| **In-Browser Recording** | **Native 10s Mic Recorder** | External file import | Cloud recorder |
| **Long-Text Narration** | **Phonetic Sentence Chunker** | Single pass | Cloud streaming |
| **License** | **AGPL-3.0** | GPL-3.0 | Proprietary |

---

## 🚀 Quickstart (Run Locally in 2 Minutes)

### Option 1: Turnkey Local Launcher (Recommended)

Make sure you have Python 3.11+, Node.js 20+, and FFmpeg installed:

```bash
# 1. Clone repository
git clone https://github.com/Yash-Raw/VoiceRep.git
cd VoiceRep

# 2. Run the turnkey launcher
chmod +x run-local.sh
./run-local.sh
```

The script automatically detects hardware acceleration (`mps` / `cuda`), runs database migrations, and boots:
- **Web App:** [http://localhost:3000](http://localhost:3000)
- **FastAPI API & Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Docker Compose (1 Command)

```bash
docker compose up -d --build
```

Services started:
- `db`: PostgreSQL 16 (on port `:5432`)
- `redis`: Redis 7 (on port `:6379`)
- `backend`: FastAPI API server (on port `:8000`)
- `worker`: ARQ background worker for async synthesis
- `frontend`: Next.js 16 production server (on port `:3000`)

---

## 🎙️ Core Features

### 1. In-Browser 10-Second Voice Cloning
- **Zero Software Required**: Record directly in your browser with the built-in 10-second microphone recorder.
- **Whisper ASR Text-Audio Alignment**: Extracts exact phonetic reference transcript from reference audio.
- **Acoustic Quality Analysis**: Analyzes speech-to-silence ratio, clipping distortion, sample rate, and volume.
- **Affirmative Consent Guard**: Enforces strict speaker authorization logging and terms compliance.

### 2. High-Fidelity Voice Studio
- **Phonetic Sentence Chunker**: Synthesizes long paragraphs without audio truncation or ODE solver hallucination.
- **Acoustic Sliders**: Customize speaking tempo (0.5x–2.0x), similarity boost, and stability.
- **Waveform Player**: Custom scrubbable audio player with HTTP 206 byte-range seeking and instant MP3 export.
- **Generation History**: Comprehensive log of past generations with direct playback.

### 3. Voice Agents (v1.1 Milestone)
- The conversational full-duplex agent module is scheduled for the v1.1 milestone. Database models and WebSocket foundations are in place.

---

## 🖥️ Hardware Acceleration Matrix

| Platform | Device String | Performance | Recommended Settings |
| :--- | :--- | :--- | :--- |
| **Apple Silicon (M1/M2/M3/M4)** | `mps` (Auto-detected) | ~0.35–0.50x RTF | `SELF_HOSTED_NFE_STEPS=32` |
| **NVIDIA GPU (RTX 3060/4090)** | `cuda` (Auto-detected) | ~0.15–0.25x RTF | `SELF_HOSTED_NFE_STEPS=32` |
| **CPU Only (Intel / AMD)** | `cpu` | ~1.5–3.0x RTF | `SELF_HOSTED_NFE_STEPS=16` |

---

## 🧪 Automated Testing

Run the full Pytest test suite:

```bash
cd backend
pytest -v
```

Tests verify:
- Safe concurrent inference under `asyncio.Semaphore(1)` barrier
- Phonetic chunking and audio stitching for long text (>180 chars)
- Path traversal protection on local storage (`403 Forbidden` on `../../`)
- End-to-end voice cloning lifecycle and database ownership isolation

---

## 📄 License

VoiceRep is licensed under the **[GNU Affero General Public License v3.0 (AGPL-3.0)](./LICENSE)**.
Under AGPL-3.0, any modified network or cloud deployment must make its full source code available to users.
