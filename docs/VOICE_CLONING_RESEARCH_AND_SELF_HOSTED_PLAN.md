# Voice Cloning Research & Self-Hosted Implementation Plan

## 1. Executive Summary

VoiceRep's core architectural principle is: **"Upload an authorized voice sample once, deploy everywhere."**
Commercial providers like ElevenLabs impose subscription paywalls on instant voice cloning (requiring paid Starter plans at $5+/month) and bill per character.

This document details:
1. The landscape of free, open-source, and low-cost voice cloning alternatives.
2. The engineering and mathematical mechanics of how modern zero-shot voice cloning works.
3. How to build and integrate an independent, 100% free, self-hosted voice cloning engine into VoiceRep without breaking existing interfaces.

---

## 2. Alternatives Landscape: Open-Source Models & Low-Cost APIs

### A. Open-Source State-of-the-Art (100% Free & Self-Hostable)

| Model | Organization | License | Architecture | Min Reference Audio | Key Strengths & Performance |
|---|---|---|---|---|---|
| **F5-TTS** | SWivid / FDU | **MIT** | Non-autoregressive DiT + Flow Matching + ConvNeXt V2 + Vocos/BigVGAN | **3 – 15s** | Ultra-high speaker similarity; no phoneme alignment needed; Real-Time Factor (RTF) ~0.15; runs on Mac Metal (MPS/MLX) and NVIDIA CUDA; zero hallucinations. |
| **CosyVoice 2** | Alibaba QwenAudio | **Apache 2.0** | Qwen2.5-0.5B + FSQ + Chunk-Aware Causal Flow Matching | **3 – 10s** | Built for **conversational AI agents**; bidirectional streaming latency **~150ms**; cross-lingual code-switching. |
| **Chatterbox / Chatterbox-Turbo** | Resemble AI | **MIT** | 0.5B Llama backbone + T3 token generator + S3Gen Flow Matching | **5 – 10s** | Commercial MIT license; expressive paralinguistic controls (`[laugh]`, `[cough]`); 350M Turbo variant. |
| **Fish Speech 1.5** | Fish Audio | **Apache 2.0 / CC** | Dual-autoregressive Transformer + Dual-codebook VQ-GAN | **5 – 15s** | High naturalness; prompt-directed emotion control; multi-character dialogue synthesis. |
| **OpenVoice v2** | MyShell.ai | **MIT** | Two-stage: Base TTS + Tone Color Converter | **2 – 5s** | Extremely fast on CPU/MPS; separates emotion/accent from speaker timbre. |
| **StyleTTS 2** | Columbia / Li et al. | **MIT** | Style Diffusion + SLM Adversarial Discriminator + HiFi-GAN | **10 – 30s** | Human-level prosody on English; continuous pitch modeling. |

### B. Ultra-Low-Cost Hosted Alternatives
- **Fish Audio API**: ~$0.006 to $0.015 per 1,000 characters; pay-as-you-go voice cloning.
- **Serverless GPU Hosting (Modal / RunPod / Replicate)**: Deploying F5-TTS or CosyVoice 2 on serverless GPUs ($0.15–$0.35/hour), costing **~$0.0001 per generation** with $0 idle cost.

---

## 3. How Voice Cloning Actually Works

Voice cloning decomposes speech synthesis into three core components:

```text
               1. SPEAKER EXTRACTION
Reference Audio ───► Acoustic / Timbre Encoder ───► Speaker Embedding / Prompt Prefix
                                                              │
                                                              ▼
               2. ACOUSTIC SEQUENCE GENERATION                │
Target Text     ───► Text Tokenizer ───────────► Generative Core ───► Intermediate Acoustic
                                                 (AR or Flow Matching)  Representation
                                                              │       (Mel-Spectrogram /
                                                              ▼        Codec Tokens)
               3. WAVEFORM RECONSTRUCTION                     │
                                                 Neural Vocoder  ───► High-Fidelity Audio
                                                 (Vocos / BigVGAN)    Waveform (WAV/MP3)
```

### A. Disentanglement & Acoustic Feature Representation
1. **Linguistic content**: *What* is spoken (words, phonemes).
2. **Timbre / Vocal tract acoustics**: *Who* speaks (formants, resonance, fundamental pitch range).
3. **Prosody / Style**: *How* it is spoken (intonation, cadence, stress, micro-pauses).

To replicate a voice, the model extracts the speaker's acoustic timbre without memorizing the linguistic content of the reference recording.

### B. The Generative Paradigms

#### 1. Autoregressive Codec Language Models (VALL-E, XTTS, Fish Speech)
- Audio is converted into discrete tokens via Neural Audio Codecs (EnCodec, SoundStream) with Residual Vector Quantization (RVQ).
- The language model predicts target audio tokens sequentially: `P(target_tokens | prompt_audio_tokens, target_text)`.
- *Drawbacks*: Slow sequential decoding and potential hallucinations (word skipping, stuttering, looping).

#### 2. Non-Autoregressive Conditional Flow Matching (F5-TTS, CosyVoice 2)
- **Mathematical Foundation**: Flow Matching defines a continuous probability trajectory mapping Gaussian noise $x_0 \sim \mathcal{N}(0, I)$ directly to the target mel-spectrogram distribution $x_1$ via a learned vector field $v_t(x)$.
- Generates speech in **16 to 32 ODE solver steps** using optimal-transport straight paths.
- *Advantages*: Extremely low latency (RTF ~0.15), robust alignment, zero word skipping, and natural breathing/vocal fry reproduction.

### C. Neural Vocoding
The generated 2D mel-spectrogram or latent feature map is passed into a neural vocoder (e.g., **Vocos** or **BigVGAN**). The vocoder predicts raw 24kHz or 44.1kHz continuous audio waveforms using multi-scale and multi-period discriminators in a single non-autoregressive forward pass.

---

## 4. Architectural Integration in VoiceRep

Because VoiceRep utilizes the `VoiceProvider` interface (`backend/app/providers/base.py`), we integrate self-hosted cloning cleanly without altering the frontend or database schemas.

```text
                      VoiceRep Backend (FastAPI)
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ElevenLabs Provider          Self-Hosted Provider
          (Commercial Cloud)           (Local F5-TTS / CosyVoice)
                                                │
                          ┌─────────────────────┴─────────────────────┐
                          ▼                                           ▼
                 Local Host Inference                        Serverless GPU Worker
              (Apple Silicon MPS / CUDA)                    (RunPod / Modal / Replicate)
```

### Provider Dynamic Toggle
An environment variable `VOICE_PROVIDER=self_hosted` (or `elevenlabs`) selects the active engine.
When `self_hosted` is active:
- `create_voice`: Validates audio locally via `AudioService`, computes reference acoustic features, and stores reference audio in `storage/voices/{voice_id}/reference.wav`.
- `synthesize`: Generates audio locally via the flow-matching neural pipeline.
- `delete_voice`: Removes saved reference audio and metadata.
- `create_agent_session`: Provides a local streaming WebSocket session.

---

## 5. Implementation Roadmap

- [x] **Research & Evaluation**: Benchmark open-source models (F5-TTS, CosyVoice 2, Chatterbox).
- [x] **Phase 1: Self-Hosted Engine Implementation**:
  - Installed dependencies (`f5-tts`, `torch` 2.15 with Apple Silicon `mps` acceleration, `vocos`, `torchcodec`, `cached_path`).
  - Implemented `SelfHostedProvider` in `backend/app/providers/self_hosted.py`.
  - Wired provider factory in `backend/app/providers/__init__.py` supporting `settings.VOICE_PROVIDER` with transparent toggle.
- [x] **Phase 2: Local Storage & Profile Management**:
  - Reference audio, transcripts, and metadata stored in `storage/voice_profiles/{voice_id}/`.
  - Zero-shot instant voice cloning validated with `POST /api/v1/voices`.
  - Neural flow-matching speech generation validated with `POST /api/v1/generations`.
- [x] **Phase 3: Conversational Voice Agent WebSocket Streaming**:
  - Implemented bidirectional streaming WebSocket endpoint at `/api/v1/agents/ws/{session_id}`.
  - Verified initiation, user transcript handling, and agent response streaming matching the Agent Playground protocol.
- [x] **Phase 4: Verification & Automated Tests**:
  - Added comprehensive test suite in `backend/tests/test_self_hosted_provider.py`.
  - 16/16 backend tests passed (`pytest -v`).
  - Next.js production build cleanly compiled with all 11 routes.
