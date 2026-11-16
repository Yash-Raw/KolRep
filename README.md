# VoiceRep — 100% Local AI Voice Cloning Platform

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-green.svg)](https://python.org)
[![Next.js 16](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![PyTorch MPS/CUDA](https://img.shields.io/badge/PyTorch-MPS%20%7C%20CUDA-red.svg)](https://pytorch.org)
[![C2PA Cryptographic Provenance](https://img.shields.io/badge/C2PA-Provenance%20Signed-emerald.svg)](https://c2pa.org)
[![EU AI Act Article 50](https://img.shields.io/badge/EU_AI_Act-Art._50_Compliant-blue.svg)]()
[![Cloud Cost: $0.00](https://img.shields.io/badge/Cloud_Cost-$0.00-brightgreen.svg)]()

> **Clone an authorized voice locally in seconds. Power high-fidelity studio narration with dual-layer C2PA cryptographic watermarking, zero cloud costs, and 100% privacy.**

VoiceRep is an enterprise-grade, open-source AI voice platform engineered for **100% local, self-hosted execution**. Built on modern **Conditional Flow Matching Diffusion Transformers (F5-TTS DiT)** and **Whisper ASR**, VoiceRep requires zero external APIs, zero credit cards, and zero cloud bills.

Every generated waveform embeds **Dual-Layer Deepfake Protection**: an in-band imperceptible acoustic watermark surviving lossy compression, and an out-of-band X.509 digitally signed C2PA provenance manifest conforming to **EU AI Act Article 50** and **US Executive Order 14110**.

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
                    Dual-Layer Deepfake Protection
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
         In-Band Acoustic Watermark     C2PA Manifest Signing
         (QIM HAS Psychoacoustic)      (X.509 ECDSA P-256)
                    │                             │
                    └──────────────┬──────────────┘
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
| **In-Band Watermarking** | Quantization Index Modulation (QIM), Human Auditory System formant masking (2.5 kHz), Barker-16 sync, CRC-16 |
| **Provenance Signing** | C2PA specification, X.509 ECDSA (SECP256R1), ID3v2 `GEOB` / RIFF `c2pa` encapsulation |
| **Audio Processing** | FFmpeg 9.0.2 (`silencedetect`, `volumedetect`), SoundFile, Librosa, SciPy FFT |
| **Hardware Acceleration** | Apple Silicon (`mps`), NVIDIA CUDA (`cuda`), CPU fallback |
| **Database & Cache** | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic, Redis 7 |
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
| **Acoustic Watermarking** | **In-Band QIM (SNR > 40dB)** | None | Proprietary closed API |
| **C2PA Provenance Signing**| **X.509 ECDSA Container Signing**| None | Proprietary closed tags |
| **Regulatory Compliance** | **EU AI Act Art. 50 & US EO 14110** | None | Closed proprietary |
| **Public Verifier UI** | **Included (`/verify`)** | None | None |
| **License** | **AGPL-3.0** | GPL-3.0 | Proprietary |

---

## 🚀 Quickstart (Run Locally in 2 Minutes)

### Option 1: Native macOS Desktop Application (Recommended for Mac Users)

For macOS Apple Silicon (M1/M2/M3/M4) users who want a 1-click standalone desktop app with zero dependencies (no Python, Node.js, Docker, PostgreSQL, Redis, or FFmpeg required):

1. **[Download VoiceRep_1.0.0_aarch64.dmg](https://github.com/Yash-Raw/VoiceRep/releases/download/v1.0.0/VoiceRep_1.0.0_aarch64.dmg)** (SHA-256: `91c5bb06bb55ac73fc526605426b26ae1f2228a1a87288f96dda68daac7d8209`).
2. Open the disk image and drag **VoiceRep.app** into your **Applications** folder.
3. Launch **VoiceRep** and complete the first-time model setup via the in-app modal.

> **macOS First-Launch Note:** If macOS Gatekeeper shows a warning on first open, right-click `VoiceRep.app` ➔ **Open** (or approve via **System Settings ➔ Privacy & Security ➔ Open Anyway**).

---

### Option 2: Turnkey Local Launcher (Developers & Linux)

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
- **Deepfake Verifier:** [http://localhost:3000/verify](http://localhost:3000/verify)
- **FastAPI API & Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 3: Docker Compose (1 Command)

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
- **Waveform Player**: Custom scrubbable audio player with HTTP 206 byte-range seeking, instant MP3 export, and C2PA trust indicators.
- **Generation History**: Comprehensive log of past generations with direct playback.

### 3. C2PA Cryptographic Watermarking & Deepfake Protection
- **Layer 1: In-Band Acoustic Watermark (Waveform Frequency)**:
  - Embeds an inaudible 136-bit cryptographic payload (timestamp, user ID hash, generation UUID hash, CRC-16 checksum) directly into the waveform.
  - Achieves studio transparency (**SNR > 40 dB**).
  - Survives MP3 256k/128k compression, transcoding, level normalization, and metadata stripping.
- **Layer 2: C2PA Manifest & X.509 ECDSA Signing (Container Level)**:
  - Generates standard C2PA manifests recording creation actions, generative AI model assertions, and SHA-256 hash binding.
  - Digitally signed with platform X.509 ECDSA P-256 certificates.
  - Embedded in ID3v2 `GEOB` frame (`application/c2pa`) for MP3 and RIFF `c2pa` chunk for WAV.
- **Public Authenticity Inspector (`/verify`)**:
  - Anyone can drag & drop an audio file into the web inspector to extract hidden acoustic watermarks and verify C2PA signatures.
  - Downloadable `.c2pa` manifest sidecars and public X.509 authority certificates.

---

## 🛡️ Verification Endpoints & API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/verify` | Upload audio to analyze Layer 1 C2PA and Layer 2 acoustic watermark |
| `GET` | `/api/v1/verify/certificate/{generation_id}` | Retrieve cryptographic provenance certificate for a generation |
| `GET` | `/api/v1/verify/public-key` | Download VoiceRep platform X.509 signing certificate (PEM) |

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
- Dual-layer C2PA manifest signing, X.509 verification, and tamper detection
- Acoustic watermark embedding, high SNR transparency (>40dB), and CRC-16 validation
- Safe concurrent inference under `asyncio.Semaphore(1)` barrier
- Phonetic chunking and audio stitching for long text (>180 chars)
- Path traversal protection on local storage (`403 Forbidden` on `../../`)
- End-to-end voice cloning lifecycle and database ownership isolation

---

## 📄 License

VoiceRep is licensed under the **[GNU Affero General Public License v3.0 (AGPL-3.0)](./LICENSE)**.
Under AGPL-3.0, any modified network or cloud deployment must make its full source code available to users.
